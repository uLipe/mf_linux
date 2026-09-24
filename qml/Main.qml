import QtQuick
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: win
    width: 1600
    height: 960
    visible: true
    color: Theme.bg
    title: "KGM Painel" + (live.signature ? " - " + live.signature : "")

    readonly property var v: live.v
    readonly property var vt: live.vt
    readonly property bool on: live.connected
    property int page: 0

    function bit(key, n) { return on && v[key] !== undefined && ((v[key] >> n) & 1) === 1 }

    component StatusLed: Row {
        property string text
        property bool lit
        property color litColor: Theme.ok
        spacing: 8
        Rectangle {
            width: 12; height: 12; radius: 6
            anchors.verticalCenter: parent.verticalCenter
            color: parent.lit ? parent.litColor : Theme.track
            border.color: parent.lit ? Qt.lighter(parent.litColor, 1.3) : Theme.border
        }
        Text { text: parent.text; color: parent.lit ? Theme.text : Theme.dim; font.pixelSize: 12 }
    }

    component CorrBar: Item {
        id: bar
        property string text
        property real value: 100
        property bool valid: true
        // 100 % = sem correcao; a barra cresce para os lados, saturando em 50 e 150 %.
        readonly property real frac: valid ? Math.max(-1, Math.min(1, (value - 100) / 50)) : 0
        implicitHeight: 34
        Text { text: bar.text; color: Theme.label; font.pixelSize: 12 }
        Text {
            anchors.right: parent.right
            text: bar.valid ? bar.value.toFixed(0) + " %" : "--"
            color: Theme.text; font.pixelSize: 12; font.family: Theme.mono
        }
        Rectangle {
            id: barTrack
            y: 20; width: bar.width; height: 8; radius: 4
            color: Theme.track
            Rectangle {
                height: barTrack.height; radius: 4
                x: bar.frac < 0 ? barTrack.width / 2 * (1 + bar.frac) : barTrack.width / 2
                width: Math.abs(bar.frac) * barTrack.width / 2
                color: bar.frac >= 0 ? Theme.accent : Theme.accent2
                Behavior on width { NumberAnimation { duration: 90 } }
            }
            Rectangle { x: barTrack.width / 2 - 1; width: 2; height: barTrack.height; color: Theme.tick }
        }
    }

    component Panel: Rectangle {
        color: Theme.panel
        radius: 6
        border.color: Theme.border
    }

    component TabButton: Rectangle {
        property string text
        property int index
        width: label.implicitWidth + 28; height: 30; radius: 5
        color: win.page === index ? Theme.track : "transparent"
        Text {
            id: label
            anchors.centerIn: parent
            text: parent.text
            color: win.page === parent.index ? Theme.text : Theme.dim
            font.pixelSize: 13
        }
        MouseArea { anchors.fill: parent; onClicked: win.page = parent.index }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            StatusLed { text: on ? live.signature : "offline"; lit: on }
            TabButton { text: "Painel"; index: 0 }
            TabButton { text: "Monitor"; index: 1 }
            TabButton { text: "Tabelas"; index: 2 }
            TabButton { text: "Configuração"; index: 3 }
            Item { Layout.fillWidth: true }
            Text {
                text: on ? "" : live.error
                color: Theme.warn; font.pixelSize: 12
                elide: Text.ElideRight
                Layout.maximumWidth: 480
            }
            Text {
                text: "ECU %1 Hz   |   %2 fps   |   %3".arg(live.pollHz.toFixed(0)).arg(live.fps.toFixed(0)).arg(live.renderer)
                color: Theme.dim; font.pixelSize: 12; font.family: Theme.mono
            }
        }

        // ------------------------------------------------------------- Painel
        RowLayout {
            visible: win.page === 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 3
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "RPM"; unit: "rpm"; valid: on
                            value: v.rpm ?? 0; textValue: vt.rpm ?? 0
                            maxValue: 8000; warnFrom: 6500; ticks: 16
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "MAP"; unit: "kPa"; valid: on
                            value: v.map ?? 0; textValue: vt.map ?? 0
                            maxValue: 250; ticks: 10; fillColor: Theme.accent2
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "SONDA"; unit: "AFR"; valid: on; decimals: 1
                            value: v.afr ?? 10; textValue: vt.afr ?? 0; marker: v.afrTarget ?? NaN
                            minValue: 10; maxValue: 20; ticks: 10
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "IGNIÇÃO"; unit: "°"; valid: on
                            value: v.advance ?? 0; textValue: vt.advance ?? 0
                            minValue: -10; maxValue: 50; ticks: 12; fillColor: Theme.marker
                        }
                    }
                }

                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 2
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 6
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "MOTOR"; unit: "°C"; valid: on
                            value: v.clt ?? -40; textValue: vt.clt ?? 0
                            minValue: -40; maxValue: 130; warnFrom: 105; ticks: 17
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "AR"; unit: "°C"; valid: on
                            value: v.iat ?? -40; textValue: vt.iat ?? 0
                            minValue: -40; maxValue: 100; warnFrom: 60; ticks: 14
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "TENSÃO"; unit: "V"; valid: on; decimals: 1
                            value: v.battery ?? 8; textValue: vt.battery ?? 0
                            minValue: 8; maxValue: 16; warnFrom: 15; ticks: 8
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "TPS"; unit: "%"; valid: on
                            value: v.tps ?? 0; textValue: vt.tps ?? 0
                            maxValue: 100; ticks: 10; fillColor: Theme.accent2
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "INJEÇÃO"; unit: "ms"; valid: on; decimals: 2
                            value: v.pw1 ?? 0; textValue: vt.pw1 ?? 0
                            maxValue: 20; ticks: 10
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "DWELL"; unit: "ms"; valid: on; decimals: 2
                            value: v.dwell ?? 0; textValue: vt.dwell ?? 0
                            maxValue: 8; ticks: 8; fillColor: Theme.marker
                        }
                        ArcGauge {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            label: "VE"; unit: "%"; valid: on
                            value: v.ve ?? 0; textValue: vt.ve ?? 0
                            maxValue: 150; ticks: 6
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 2
                    columns: 2
                    rowSpacing: 10; columnSpacing: 10
                    StripChart {
                        id: cRpm
                        Layout.fillWidth: true; Layout.fillHeight: true
                        title: "RPM"; key1: "rpm"; yMax: 8000; yTick: 2000
                    }
                    StripChart {
                        id: cMap
                        Layout.fillWidth: true; Layout.fillHeight: true
                        title: "CARGA"; key1: "map"; name1: "MAP kPa"; key2: "tps"; name2: "TPS %"
                        yMax: 250; yTick: 50; color1: Theme.accent2
                    }
                    StripChart {
                        id: cAfr
                        Layout.fillWidth: true; Layout.fillHeight: true
                        title: "SONDA"; key1: "afr"; name1: "medido"; key2: "afrTarget"; name2: "alvo"
                        yMin: 10; yMax: 20; yTick: 2
                    }
                    StripChart {
                        id: cAdv
                        Layout.fillWidth: true; Layout.fillHeight: true
                        title: "IGNIÇÃO / DWELL"; key1: "advance"; name1: "avanço °"; key2: "dwell"; name2: "dwell ms"
                        yMin: -10; yMax: 50; yTick: 10; color1: Theme.marker; color2: Theme.accent
                    }
                }
            }

            Panel {
                Layout.preferredWidth: 280
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Text { text: "ESTADO"; color: Theme.label; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 1 }
                    GridLayout {
                        columns: 2
                        rowSpacing: 8; columnSpacing: 12
                        StatusLed { text: "Sincronia"; lit: bit("spark", 7) }
                        StatusLed { text: "Meia sincronia"; lit: bit("status3", 4); litColor: Theme.marker }
                        StatusLed { text: "Funcionando"; lit: bit("engine", 0) }
                        StatusLed { text: "Partida"; lit: bit("engine", 1); litColor: Theme.marker }
                        StatusLed { text: "Pós-partida"; lit: bit("engine", 2); litColor: Theme.accent2 }
                        StatusLed { text: "Aquecimento"; lit: bit("engine", 3); litColor: Theme.accent2 }
                        StatusLed { text: "Aceleração"; lit: bit("engine", 4); litColor: Theme.accent2 }
                        StatusLed { text: "Desaceleração"; lit: bit("engine", 5); litColor: Theme.accent2 }
                        StatusLed { text: "Corte (DFCO)"; lit: bit("status1", 4); litColor: Theme.marker }
                        StatusLed { text: "Marcha lenta"; lit: bit("spark", 6) }
                        StatusLed { text: "Limitador"; lit: bit("spark", 2) || bit("spark", 3); litColor: Theme.warn }
                        StatusLed { text: "Largada"; lit: bit("spark", 0) || bit("spark", 1); litColor: Theme.warn }
                        StatusLed { text: "Eletroventilador"; lit: bit("status4", 3); litColor: Theme.accent2 }
                        StatusLed { text: "Ar condicionado"; lit: bit("airConStatus", 1); litColor: Theme.accent2 }
                        StatusLed { text: "Burn pendente"; lit: bit("status4", 4); litColor: Theme.marker }
                        StatusLed { text: "Erro"; lit: bit("spark", 5); litColor: Theme.warn }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border; Layout.topMargin: 6 }

                    Text { text: "ENRIQUECIMENTO"; color: Theme.label; font.pixelSize: 12; font.weight: Font.Medium; font.letterSpacing: 1 }
                    CorrBar { Layout.fillWidth: true; text: "Total (gammaE)"; valid: on; value: vt.gammaE ?? 100 }
                    CorrBar { Layout.fillWidth: true; text: "Aquecimento"; valid: on; value: vt.wueCorrection ?? 100 }
                    CorrBar { Layout.fillWidth: true; text: "Temperatura do ar"; valid: on; value: vt.iatCorrection ?? 100 }
                    CorrBar { Layout.fillWidth: true; text: "Bateria"; valid: on; value: vt.batCorrection ?? 100 }
                    CorrBar { Layout.fillWidth: true; text: "Sonda"; valid: on; value: vt.egoCorrection ?? 100 }
                    CorrBar { Layout.fillWidth: true; text: "Aceleração"; valid: on; value: vt.accelEnrich ?? 100 }

                    Item { Layout.fillHeight: true }

                    Text {
                        text: on ? "perdas de sincronia: %1   |   seg: %2".arg(vt.syncLoss ?? 0).arg(vt.secl ?? 0) : ""
                        color: Theme.dim; font.pixelSize: 11; font.family: Theme.mono
                    }
                }
            }
        }

        TableEditor {
            visible: win.page === 2
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        ConfigView {
            visible: win.page === 3
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        // ------------------------------------------------------------ Monitor
        ColumnLayout {
            visible: win.page === 1
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            Row {
                spacing: 8
                Rectangle {
                    width: 16; height: 16; radius: 3
                    color: showAll ? Theme.accent : Theme.track
                    MouseArea { anchors.fill: parent; onClicked: showAll = !showAll }
                }
                Text { text: "mostrar canais sem rótulo no MasterFuel"; color: Theme.label; font.pixelSize: 12 }
            }

            GridView {
                id: grid
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                cellWidth: width / 4
                cellHeight: 76
                model: live.channels.filter(c => showAll || c.label !== "")
                delegate: Item {
                    required property var modelData
                    width: grid.cellWidth; height: grid.cellHeight
                    Panel {
                        anchors.fill: parent
                        anchors.margins: 4
                        Text {
                            x: 12; y: 8
                            text: modelData.label || modelData.key
                            color: Theme.label; font.pixelSize: 11; font.letterSpacing: 0.5
                        }
                        Text {
                            anchors.right: parent.right; anchors.rightMargin: 12
                            anchors.bottom: parent.bottom; anchors.bottomMargin: 8
                            textFormat: Text.PlainText
                            text: {
                                const x = vt[modelData.key]
                                if (!on || x === undefined) return "--"
                                if (modelData.unit === "bits") return "0x" + x.toString(16).toUpperCase().padStart(2, "0")
                                return x.toFixed(Math.min(modelData.decimals, 2)) + " " + modelData.unit
                            }
                            color: Theme.text; font.pixelSize: 24; font.family: Theme.mono
                        }
                    }
                }
            }
        }
    }

    onPageChanged: {
        if (page === 2 && !editor.currentName) editor.open("ve")
        if (page === 3 && !config.current) config.open(config.panels[0].id)
    }

    property bool showAll: false

    Connections {
        target: live
        function onFrameChanged() {
            if (win.page !== 0)
                return
            cRpm.push(live.v); cMap.push(live.v); cAfr.push(live.v); cAdv.push(live.v)
        }
    }
}
