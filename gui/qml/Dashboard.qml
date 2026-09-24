import QtQuick
import QtQuick.Layouts

Item {
    id: dash

    readonly property var v: backend.live
    function n(k) { var x = v[k]; return x === undefined ? 0 : x }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        // fillHeight explicito: sem ele a linha herda o dos gauges e rouba a altura dos graficos.
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: dash.height * 0.38
            spacing: 10
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "RPM"; unit: "rpm"; value: n("rpm")
                maximum: 8000; warning: 6500; danger: 7200; ticks: 8
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "MAP"; unit: "kPa"; value: n("map")
                maximum: 250; ticks: 5
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "SONDA"; unit: "AFR"; value: n("afr"); decimals: 1
                minimum: 10; maximum: 20; ticks: 10
                subtitle: "alvo " + n("afrTarget").toFixed(1)
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "IGNIÇÃO"; unit: "°"; value: n("advance")
                minimum: -10; maximum: 50; ticks: 6
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: dash.height * 0.20
            columns: 8
            columnSpacing: 6
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "MOTOR"; unit: "°C"; value: n("clt")
                minimum: -40; maximum: 130; warning: 100; danger: 110; ticks: 17
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "AR"; unit: "°C"; value: n("iat")
                minimum: -40; maximum: 100; warning: 60; danger: 75; ticks: 14
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "TENSÃO"; unit: "V"; value: n("battery"); decimals: 1
                minimum: 8; maximum: 16; warning: 14.8; danger: 15.5; ticks: 8
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "TPS"; unit: "%"; value: n("tps"); ticks: 10
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "INJEÇÃO"; unit: "ms"; value: n("pw1"); decimals: 2
                maximum: 20; warning: 15; danger: 18; ticks: 10
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "DWELL"; unit: "ms"; value: n("actualDwell"); decimals: 2
                maximum: 6; ticks: 6
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "VE"; unit: "%"; value: n("ve")
                maximum: 150; ticks: 6
            }
            Gauge {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: "CORR. SONDA"; unit: "%"; value: n("egoCorrection")
                minimum: 70; maximum: 130; ticks: 6
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10
            StripChart {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "RPM"; key: "rpm"; maximum: 8000
            }
            StripChart {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "MAP (kPa)"; key: "map"; maximum: 250; lineColor: "#7ee081"
            }
            StripChart {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "SONDA × ALVO (AFR)"; key: "afr"; refKey: "afrTarget"
                minimum: 10; maximum: 20; lineColor: "#c792ea"
            }
        }
    }
}
