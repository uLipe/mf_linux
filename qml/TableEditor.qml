import QtQuick
import QtQuick.Layouts
import QtGraphs

Item {
    id: root

    property bool show3d: true
    readonly property int n: editor.size

    // Azul (menor) -> vermelho (maior), escuro o bastante para texto branco.
    function heat(t) { return Qt.hsla((1 - Math.max(0, Math.min(1, t))) * 0.66, 0.62, 0.38, 1) }

    component Field: Rectangle {
        property alias text: input.text
        property alias input: input
        property string placeholder
        signal accepted
        implicitWidth: 70
        implicitHeight: 28
        radius: 5
        color: Theme.bg
        border.color: input.activeFocus ? Theme.accent : Theme.border
        TextInput {
            id: input
            anchors.fill: parent
            anchors.margins: 6
            color: Theme.text
            font.pixelSize: 12
            font.family: Theme.mono
            verticalAlignment: TextInput.AlignVCenter
            selectByMouse: true
            onAccepted: parent.accepted()
            Keys.onEscapePressed: { text = ""; keys.forceActiveFocus() }
        }
        Text {
            anchors.fill: input
            verticalAlignment: Text.AlignVCenter
            text: parent.placeholder
            color: Theme.dim
            font.pixelSize: 12
            visible: input.text === "" && !input.activeFocus
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 10

        // ------------------------------------------------------- lista de tabelas
        Rectangle {
            Layout.preferredWidth: 180
            Layout.fillHeight: true
            color: Theme.panel
            radius: 6
            border.color: Theme.border

            Flickable {
                anchors.fill: parent
                anchors.margins: 10
                contentHeight: groups.implicitHeight
                clip: true
                Column {
                    id: groups
                    width: parent.width
                    spacing: 4
                    Repeater {
                        model: editor.groups
                        delegate: Column {
                            required property var modelData
                            width: groups.width
                            spacing: 2
                            Text {
                                text: modelData.group.toUpperCase()
                                color: Theme.dim
                                font.pixelSize: 10
                                font.letterSpacing: 1
                                topPadding: 8
                                bottomPadding: 2
                            }
                            Repeater {
                                model: modelData.tables
                                delegate: Rectangle {
                                    required property var modelData
                                    width: groups.width
                                    height: 26
                                    radius: 4
                                    color: editor.currentName === modelData.name ? Theme.track : "transparent"
                                    Text {
                                        x: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.label
                                        color: editor.currentName === modelData.name ? Theme.text : Theme.label
                                        font.pixelSize: 12
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: { editor.open(modelData.name); keys.forceActiveFocus() }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            // ------------------------------------------------------- ferramentas
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
                        text: editor.label + (editor.unit ? "  (" + editor.unit + ")" : "")
                        color: Theme.text
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        Layout.rightMargin: 10
                    }
                    ToolButton { text: "−"; active: n > 0; onClicked: { editor.nudge(-1); keys.forceActiveFocus() } }
                    ToolButton { text: "+"; active: n > 0; onClicked: { editor.nudge(1); keys.forceActiveFocus() } }
                    Field {
                        id: valueField
                        placeholder: "valor"
                        onAccepted: if (editor.setValue(text)) { text = ""; keys.forceActiveFocus() }
                    }
                    Field {
                        id: pctField
                        placeholder: "± %"
                        implicitWidth: 56
                        onAccepted: {
                            const p = parseFloat(text.replace(",", "."))
                            if (!isNaN(p)) { editor.scaleBy(p); text = ""; keys.forceActiveFocus() }
                        }
                    }
                    ToolButton { text: "Interpolar"; active: n > 0; onClicked: { editor.interpolate(); keys.forceActiveFocus() } }
                    ToolButton { text: "Suavizar"; active: n > 0; onClicked: { editor.smooth(); keys.forceActiveFocus() } }
                    ToolButton { text: "Desfazer"; active: editor.canUndo; onClicked: { editor.undo(); keys.forceActiveFocus() } }
                    ToolButton { text: "Reler"; active: n > 0; onClicked: editor.reload() }
                    Item { Layout.fillWidth: true }
                    ToolButton { text: root.show3d ? "Ocultar 3D" : "Mostrar 3D"; onClicked: root.show3d = !root.show3d }
                    ToolButton {
                        text: "Gravar na flash"
                        accent: editor.dirty
                        active: editor.dirty && live.connected
                        onClicked: editor.burn()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                // ------------------------------------------------------- grade
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 3
                    color: Theme.panel
                    radius: 6
                    border.color: Theme.border

                    Item {
                        id: keys
                        anchors.fill: parent
                        focus: true
                        Keys.onPressed: event => {
                            const ext = (event.modifiers & Qt.ShiftModifier) !== 0
                            const ctrl = (event.modifiers & Qt.ControlModifier) !== 0
                            const big = ctrl ? 10 : 1
                            switch (event.key) {
                            case Qt.Key_Up: editor.move(-1, 0, ext); break
                            case Qt.Key_Down: editor.move(1, 0, ext); break
                            case Qt.Key_Left: editor.move(0, -1, ext); break
                            case Qt.Key_Right: editor.move(0, 1, ext); break
                            case Qt.Key_Plus: case Qt.Key_Equal: case Qt.Key_PageUp: editor.nudge(big); break
                            case Qt.Key_Minus: case Qt.Key_PageDown: editor.nudge(-big); break
                            case Qt.Key_I: editor.interpolate(); break
                            case Qt.Key_S: editor.smooth(); break
                            case Qt.Key_Z: if (ctrl) editor.undo(); else return; break
                            case Qt.Key_A: if (ctrl) editor.selectAll(); else return; break
                            default:
                                // digitar um numero abre o campo de valor ja com o caractere
                                if (/^[0-9.,]$/.test(event.text)) {
                                    valueField.text = event.text
                                    valueField.input.forceActiveFocus()
                                } else {
                                    return
                                }
                            }
                            event.accepted = true
                        }
                    }

                    Text {
                        visible: n === 0
                        anchors.centerIn: parent
                        text: editor.currentName ? editor.status : "escolha uma tabela"
                        color: Theme.dim
                        font.pixelSize: 14
                    }

                    Item {
                        id: plot
                        visible: n > 0
                        anchors.fill: parent
                        anchors.margins: 12
                        anchors.leftMargin: 52
                        anchors.bottomMargin: 30
                        readonly property real cw: width / Math.max(1, n)
                        readonly property real ch: height / Math.max(1, n)

                        Grid {
                            columns: Math.max(1, n)
                            Repeater {
                                model: editor.model
                                delegate: Rectangle {
                                    required property int index
                                    required property string text
                                    required property real norm
                                    required property bool selected
                                    required property bool changed
                                    width: plot.cw
                                    height: plot.ch
                                    color: root.heat(norm)
                                    border.color: selected ? "white" : Theme.bg
                                    border.width: selected ? 2 : 1
                                    Text {
                                        anchors.centerIn: parent
                                        text: parent.text
                                        color: "white"
                                        font.pixelSize: Math.min(15, plot.ch * 0.42, plot.cw * 0.3)
                                        font.family: Theme.mono
                                        font.bold: parent.selected
                                    }
                                    // celula diferente do que esta na flash
                                    Rectangle {
                                        visible: parent.changed
                                        anchors.top: parent.top; anchors.right: parent.right
                                        anchors.margins: 3
                                        width: 6; height: 6; radius: 3
                                        color: Theme.marker
                                    }
                                }
                            }
                        }

                        // ponto de operacao: onde a ECU esta lendo a tabela agora
                        Rectangle {
                            visible: editor.hasCursor && editor.cursorX >= 0 && live.connected
                            width: 22; height: 22; radius: 11
                            x: (editor.cursorX + 0.5) * plot.cw - width / 2
                            y: (editor.cursorY + 0.5) * plot.ch - height / 2
                            color: "transparent"
                            border.color: "white"
                            border.width: 3
                            Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: "white" }
                            Behavior on x { NumberAnimation { duration: 70 } }
                            Behavior on y { NumberAnimation { duration: 70 } }
                        }

                        MouseArea {
                            anchors.fill: parent
                            function cell(m) { return [Math.floor(m.y / plot.ch), Math.floor(m.x / plot.cw)] }
                            onPressed: m => {
                                const c = cell(m)
                                editor.select(c[0], c[1], (m.modifiers & Qt.ShiftModifier) !== 0)
                                keys.forceActiveFocus()
                            }
                            onPositionChanged: m => { if (pressed) { const c = cell(m); editor.select(c[0], c[1], true) } }
                        }

                        Repeater {
                            model: editor.loadAxis
                            delegate: Text {
                                required property int index
                                required property var modelData
                                x: -width - 8
                                y: (index + 0.5) * plot.ch - height / 2
                                text: modelData
                                color: Theme.label
                                font.pixelSize: 11
                                font.family: Theme.mono
                            }
                        }
                        Repeater {
                            model: editor.rpmAxis
                            delegate: Text {
                                required property int index
                                required property var modelData
                                x: (index + 0.5) * plot.cw - width / 2
                                y: plot.height + 8
                                text: modelData
                                color: Theme.label
                                font.pixelSize: 11
                                font.family: Theme.mono
                            }
                        }
                    }
                }

                // ------------------------------------------------------- 3D
                Rectangle {
                    visible: root.show3d
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 2
                    color: Theme.panel
                    radius: 6
                    border.color: Theme.border

                    Surface3D {
                        id: surface
                        anchors.fill: parent
                        anchors.margins: 4
                        shadowQuality: Graphs3D.ShadowQuality.None
                        selectionMode: Graphs3D.SelectionFlag.None
                        msaaSamples: 4
                        cameraPreset: Graphs3D.CameraPreset.IsometricLeftHigh
                        // sem isso a proporcao sai dos intervalos (RPM 700..5000 x carga 20..100)
                        horizontalAspectRatio: 1.0
                        aspectRatio: 1.4
                        theme: GraphsTheme {
                            colorScheme: GraphsTheme.ColorScheme.Dark
                            backgroundVisible: false
                            plotAreaBackgroundVisible: false
                            labelBackgroundVisible: false
                            labelBorderVisible: false
                            labelTextColor: Theme.label
                            grid.mainColor: Theme.tick
                            colorStyle: GraphsTheme.ColorStyle.RangeGradient
                            baseGradients: [
                                Gradient {
                                    GradientStop { position: 0.0; color: root.heat(0) }
                                    GradientStop { position: 0.25; color: root.heat(0.25) }
                                    GradientStop { position: 0.5; color: root.heat(0.5) }
                                    GradientStop { position: 0.75; color: root.heat(0.75) }
                                    GradientStop { position: 1.0; color: root.heat(1) }
                                }
                            ]
                        }
                        axisX: Value3DAxis { title: "RPM"; titleVisible: true; labelFormat: "%.0f" }
                        axisY: Value3DAxis { title: editor.unit; titleVisible: true; labelFormat: "%.0f" }
                        axisZ: Value3DAxis { title: "carga"; titleVisible: true; labelFormat: "%.0f" }

                        Surface3DSeries {
                            id: series
                            drawMode: Surface3DSeries.DrawSurfaceAndWireframe
                            shading: Surface3DSeries.Shading.Smooth
                            wireframeColor: "#40ffffff"
                        }
                    }
                    Text {
                        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 10
                        text: "arraste para girar  ·  roda para zoom"
                        color: Theme.dim; font.pixelSize: 11
                    }
                }
            }

            // ------------------------------------------------------- status
            RowLayout {
                Layout.fillWidth: true
                spacing: 16
                Text { text: editor.selectionInfo; color: Theme.text; font.pixelSize: 12; font.family: Theme.mono }
                Item { Layout.fillWidth: true }
                Text {
                    text: editor.status
                    color: editor.dirty ? Theme.marker : Theme.dim
                    font.pixelSize: 12
                    elide: Text.ElideLeft
                    Layout.maximumWidth: 700
                }
            }
            Text {
                text: "setas: mover  ·  shift: estender  ·  +/−: passo (ctrl ×10)  ·  número + enter: valor  ·  I: interpolar  ·  S: suavizar  ·  ctrl+Z: desfazer   —   toda edição vale no motor na hora"
                color: Theme.dim
                font.pixelSize: 11
            }
        }
    }

    Connections {
        target: editor
        function onCellsChanged() { editor.fillSurface(series) }
    }
}
