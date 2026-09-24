import QtQuick
import QtQuick.Layouts

Item {
    id: root

    readonly property bool on: live.connected
    readonly property var vt: live.vt

    function ledOn(l) { return on && vt[l.key] !== undefined && ((vt[l.key] >> l.bit) & 1) === 1 }

    component ConfigRow: Item {
        id: cr
        property var row
        readonly property bool editable: row.ready && row.enabled && root.on
        implicitHeight: body.implicitHeight + 8
        opacity: row.enabled ? 1 : 0.45

        ColumnLayout {
            id: body
            y: 4
            width: cr.width
            spacing: 3

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: 6; height: 6; radius: 3
                    color: cr.row.changed ? Theme.marker : "transparent"
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1
                    Text {
                        Layout.fillWidth: true
                        text: cr.row.label
                        color: Theme.text; font.pixelSize: 13
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: text !== ""
                        text: [cr.row.detail, cr.row.reboot ? "requer reiniciar a ECU" : ""].filter(s => s).join("  ·  ")
                        color: Theme.dim; font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                }

                Rectangle {
                    readonly property bool lit: visible && root.ledOn(cr.row.live)
                    visible: !!cr.row.live
                    width: 12; height: 12; radius: 6
                    color: lit ? Theme[cr.row.live.color] : Theme.track
                    border.color: lit ? Qt.lighter(color, 1.3) : Theme.border
                }

                RowLayout {
                    visible: cr.row.kind === "num"
                    spacing: 4
                    ToolButton { text: "−"; active: cr.editable; onClicked: config.nudge(cr.row.index, -1) }
                    Rectangle {
                        implicitWidth: 76; implicitHeight: 28; radius: 5
                        color: Theme.bg
                        border.color: input.activeFocus ? Theme.accent : Theme.border
                        TextInput {
                            id: input
                            anchors.fill: parent
                            anchors.margins: 6
                            horizontalAlignment: TextInput.AlignRight
                            verticalAlignment: TextInput.AlignVCenter
                            color: Theme.text; font.pixelSize: 13; font.family: Theme.mono
                            selectByMouse: true
                            readOnly: !cr.editable
                            text: cr.row.ready ? cr.row.text : "--"
                            onActiveFocusChanged: if (activeFocus) selectAll()
                            onAccepted: { config.setText(cr.row.index, text); focus = false }
                            Keys.onEscapePressed: { text = cr.row.text; focus = false }
                        }
                    }
                    ToolButton { text: "+"; active: cr.editable; onClicked: config.nudge(cr.row.index, 1) }
                    Text {
                        Layout.preferredWidth: 60
                        text: cr.row.unit ?? ""
                        color: Theme.dim; font.pixelSize: 11
                    }
                }

                Row {
                    visible: cr.row.kind === "choice"
                    spacing: 4
                    Repeater {
                        model: cr.row.options ?? []
                        delegate: Rectangle {
                            required property var modelData
                            readonly property bool sel: cr.row.ready && cr.row.raw === modelData.raw
                            width: chip.implicitWidth + 18; height: 28; radius: 5
                            color: sel ? Theme.accent : (chipArea.containsMouse && cr.editable ? Theme.tick : Theme.track)
                            Text {
                                id: chip
                                anchors.centerIn: parent
                                text: modelData.text
                                color: parent.sel ? Theme.bg : Theme.label
                                font.pixelSize: 11
                                font.weight: parent.sel ? Font.DemiBold : Font.Normal
                            }
                            MouseArea {
                                id: chipArea
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: cr.editable && !parent.sel
                                onClicked: config.choose(cr.row.index, modelData.raw)
                            }
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                visible: cr.row.note !== ""
                text: cr.row.note
                color: Theme.marker; font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            Layout.preferredWidth: 180
            Layout.fillHeight: true
            color: Theme.panel
            radius: 6
            border.color: Theme.border

            Column {
                id: list
                anchors.fill: parent
                anchors.margins: 10
                spacing: 2
                Text {
                    text: "PAINÉIS"
                    color: Theme.dim; font.pixelSize: 10; font.letterSpacing: 1
                    topPadding: 8; bottomPadding: 2
                }
                Repeater {
                    model: config.panels
                    delegate: Rectangle {
                        required property var modelData
                        width: list.width
                        height: 26
                        radius: 4
                        color: config.current === modelData.id ? Theme.track : "transparent"
                        Text {
                            x: 10
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.title
                            color: config.current === modelData.id ? Theme.text : Theme.label
                            font.pixelSize: 12
                        }
                        MouseArea { anchors.fill: parent; onClicked: config.open(modelData.id) }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 44
                color: Theme.panel
                radius: 6
                border.color: Theme.border

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 8
                    spacing: 6
                    Text {
                        text: config.title
                        color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold
                        Layout.rightMargin: 10
                    }
                    Text {
                        Layout.fillWidth: true
                        text: config.status
                        color: Theme.dim; font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                    ToolButton { text: "Reler"; active: root.on; onClicked: config.reload() }
                    ToolButton {
                        text: "Gravar na flash"
                        accent: config.dirty
                        active: config.dirty && root.on
                        onClicked: config.burn()
                    }
                }
            }

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: columns.implicitHeight
                clip: true

                // Duas colunas balanceadas: cada grupo vai para a coluna mais baixa no momento.
                RowLayout {
                    id: columns
                    width: parent.width
                    spacing: 10
                    Repeater {
                        model: 2
                        delegate: ColumnLayout {
                            id: column
                            required property int index
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            Layout.preferredWidth: 1
                            spacing: 10
                            Repeater {
                                model: {
                                    const g = config.groups, cols = [[], []], h = [0, 0]
                                    for (const grp of g) {
                                        const c = h[0] <= h[1] ? 0 : 1
                                        cols[c].push(grp)
                                        h[c] += grp.rows.length + 1.5
                                    }
                                    return cols[column.index]
                                }
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: rows.implicitHeight + 24
                                    color: Theme.panel
                                    radius: 6
                                    border.color: Theme.border
                                    Column {
                                        id: rows
                                        x: 14; y: 12
                                        width: parent.width - 28
                                        spacing: 4
                                        Text {
                                            text: modelData.title.toUpperCase()
                                            color: Theme.label; font.pixelSize: 12
                                            font.weight: Font.Medium; font.letterSpacing: 1
                                            bottomPadding: 4
                                        }
                                        Repeater {
                                            model: modelData.rows
                                            delegate: ConfigRow {
                                                required property var modelData
                                                width: rows.width
                                                row: modelData
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
