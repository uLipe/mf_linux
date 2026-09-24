import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtGraphs

Item {
    id: view

    property var model: backend.table(backend.tableNames[list.currentIndex].name)

    // Selecao retangular em coordenadas da view (linha 0 = maior carga).
    property int curRow: 0
    property int curCol: 0
    property int anchorRow: 0
    property int anchorCol: 0
    property string typed: ""

    function heat(t) { return Qt.hsla((1 - t) * 0.66, 0.70, 0.40, 1) }

    function selected(r, c) {
        return r >= Math.min(anchorRow, curRow) && r <= Math.max(anchorRow, curRow)
            && c >= Math.min(anchorCol, curCol) && c <= Math.max(anchorCol, curCol)
    }

    function selection() {
        var out = []
        for (var r = Math.min(anchorRow, curRow); r <= Math.max(anchorRow, curRow); ++r)
            for (var c = Math.min(anchorCol, curCol); c <= Math.max(anchorCol, curCol); ++c)
                out.push([r, c])
        return out
    }

    function moveTo(r, c, extend) {
        var n = model.n
        curRow = Math.max(0, Math.min(n - 1, r))
        curCol = Math.max(0, Math.min(n - 1, c))
        if (!extend) {
            anchorRow = curRow
            anchorCol = curCol
        }
    }

    onModelChanged: { moveTo(0, 0, false); typed = "" }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 190
            Layout.fillHeight: true
            color: "#171b23"
            radius: 6
            ListView {
                id: list
                anchors.fill: parent
                anchors.margins: 4
                clip: true
                model: backend.tableNames
                delegate: ItemDelegate {
                    width: ListView.view.width
                    text: modelData.title
                    highlighted: ListView.isCurrentItem
                    onClicked: { list.currentIndex = index; grid.forceActiveFocus() }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 6

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: view.model.title
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                }
                Label {
                    text: view.model.unit ? "(" + view.model.unit + ")" : "(cru, escala depende do modo)"
                    color: "#8a93a6"
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: view.typed !== "" ? "valor: " + view.typed + "  ⏎" : ""
                    color: "#39c0ff"
                    font.pixelSize: 16
                }
            }

            Item {
                id: gridArea
                Layout.fillWidth: true
                Layout.fillHeight: true

                readonly property int n: view.model.n
                readonly property real axisW: 46
                readonly property real axisH: 24
                readonly property real cellW: n ? (width - axisW) / n : 0
                readonly property real cellH: n ? (height - axisH) / n : 0

                Repeater {
                    model: gridArea.n
                    Text {
                        x: 0
                        y: index * gridArea.cellH
                        width: gridArea.axisW - 6
                        height: gridArea.cellH
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                        text: view.model.loadAxis[index]
                        color: "#8a93a6"
                        font.pixelSize: 12
                    }
                }
                Repeater {
                    model: gridArea.n
                    Text {
                        x: gridArea.axisW + index * gridArea.cellW
                        y: gridArea.height - gridArea.axisH
                        width: gridArea.cellW
                        height: gridArea.axisH
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        text: view.model.rpmAxis[index]
                        color: "#8a93a6"
                        font.pixelSize: 12
                    }
                }

                TableView {
                    id: grid
                    x: gridArea.axisW
                    width: gridArea.width - gridArea.axisW
                    height: gridArea.height - gridArea.axisH
                    interactive: false
                    focus: true
                    model: view.model
                    columnWidthProvider: function () { return gridArea.cellW }
                    rowHeightProvider: function () { return gridArea.cellH }
                    onWidthChanged: forceLayout()
                    onHeightChanged: forceLayout()

                    delegate: Rectangle {
                        required property int row
                        required property int column
                        required property string text
                        required property real norm
                        color: view.heat(norm)
                        border.width: view.selected(row, column) ? 2 : 0.5
                        border.color: view.selected(row, column) ? "#ffffff" : "#12151b"
                        Text {
                            anchors.centerIn: parent
                            text: parent.text
                            color: "#f4f6fa"
                            font.pixelSize: Math.min(14, parent.height * 0.45)
                            font.features: { "tnum": 1 }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        function cellAt(m) {
                            return [Math.floor(m.y / gridArea.cellH), Math.floor(m.x / gridArea.cellW)]
                        }
                        onPressed: (m) => {
                            var rc = cellAt(m)
                            view.moveTo(rc[0], rc[1], m.modifiers & Qt.ShiftModifier)
                            grid.forceActiveFocus()
                        }
                        onPositionChanged: (m) => {
                            if (pressed) { var rc = cellAt(m); view.moveTo(rc[0], rc[1], true) }
                        }
                    }

                    Keys.onPressed: (e) => {
                        var ext = e.modifiers & Qt.ShiftModifier
                        var step = (e.modifiers & Qt.ControlModifier) ? 10 : 1
                        if (e.key === Qt.Key_Up) view.moveTo(view.curRow - 1, view.curCol, ext)
                        else if (e.key === Qt.Key_Down) view.moveTo(view.curRow + 1, view.curCol, ext)
                        else if (e.key === Qt.Key_Left) view.moveTo(view.curRow, view.curCol - 1, ext)
                        else if (e.key === Qt.Key_Right) view.moveTo(view.curRow, view.curCol + 1, ext)
                        else if (e.key === Qt.Key_Plus || e.key === Qt.Key_Equal) view.model.adjust(view.selection(), step)
                        else if (e.key === Qt.Key_Minus && view.typed === "") view.model.adjust(view.selection(), -step)
                        else if (e.key === Qt.Key_PageUp) view.model.adjust(view.selection(), 10)
                        else if (e.key === Qt.Key_PageDown) view.model.adjust(view.selection(), -10)
                        else if (e.key === Qt.Key_Escape) view.typed = ""
                        else if (e.key === Qt.Key_Backspace) view.typed = view.typed.slice(0, -1)
                        else if ((e.key === Qt.Key_Return || e.key === Qt.Key_Enter) && view.typed !== "") {
                            view.model.setValue(view.selection(), parseFloat(view.typed))
                            view.typed = ""
                        }
                        else if (/^[0-9.\-]$/.test(e.text)) view.typed += e.text
                        else return
                        e.accepted = true
                    }

                    // Ponto de operacao atual, interpolado entre as celulas.
                    Rectangle {
                        visible: backend.connected && !!view.model && view.model.cursorX >= 0
                        width: 16; height: 16; radius: 8
                        x: view.model ? (view.model.cursorX + 0.5) * gridArea.cellW - width / 2 : 0
                        y: view.model ? (view.model.cursorY + 0.5) * gridArea.cellH - height / 2 : 0
                        color: "transparent"
                        border.color: "#ffffff"
                        border.width: 3
                        Rectangle { anchors.centerIn: parent; width: 4; height: 4; radius: 2; color: "#ffffff" }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                text: "setas: mover · shift: selecionar · + / − : ±1 · ctrl: ±10 · digite o valor e ⏎"
                color: "#6c7486"
                font.pixelSize: 12
            }
            Repeater {
                model: view.model.warnings
                Label {
                    Layout.fillWidth: true
                    text: "⚠ " + modelData
                    color: "#ffb020"
                    font.pixelSize: 12
                }
            }
        }

        Surface3D {
            Layout.preferredWidth: view.width * 0.34
            Layout.fillHeight: true
            shadowQuality: Graphs3D.ShadowQuality.None
            cameraPreset: Graphs3D.CameraPreset.IsometricRightHigh
            theme: GraphsTheme {
                colorScheme: GraphsTheme.ColorScheme.Dark
                backgroundVisible: false
                labelBackgroundVisible: false
            }
            axisX: Value3DAxis { title: "RPM"; titleVisible: true; labelFormat: "%.0f" }
            axisZ: Value3DAxis { title: "carga"; titleVisible: true; labelFormat: "%.0f" }
            axisY: Value3DAxis {
                min: view.model.minValue
                max: Math.max(view.model.maxValue, view.model.minValue + 1)
                labelFormat: "%.0f"
            }
            Surface3DSeries {
                drawMode: Surface3DSeries.DrawFlag.DrawSurfaceAndWireframe
                shading: Surface3DSeries.Shading.Smooth
                colorStyle: GraphsTheme.ColorStyle.RangeGradient
                wireframeColor: "#1a1d24"
                baseGradient: Gradient {
                    GradientStop { position: 0.0; color: Qt.hsla(0.66, 0.7, 0.4, 1) }
                    GradientStop { position: 0.33; color: Qt.hsla(0.44, 0.7, 0.4, 1) }
                    GradientStop { position: 0.66; color: Qt.hsla(0.22, 0.7, 0.4, 1) }
                    GradientStop { position: 1.0; color: Qt.hsla(0.0, 0.7, 0.4, 1) }
                }
                dataProxy: ItemModelSurfaceDataProxy {
                    itemModel: view.model
                    rowRole: "load"
                    columnRole: "rpm"
                    xPosRole: "rpm"
                    zPosRole: "load"
                    yPosRole: "display"
                }
            }
        }
    }
}
