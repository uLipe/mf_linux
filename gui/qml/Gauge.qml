import QtQuick

Item {
    id: g

    property real value: 0
    property real minimum: 0
    property real maximum: 100
    property real warning: maximum
    property real danger: maximum
    property string label
    property string unit
    property string subtitle
    property int decimals: 0
    property int ticks: 10

    readonly property real span: maximum - minimum
    readonly property color accent: value >= danger ? "#ff5a5f" : value >= warning ? "#ffb020" : "#39c0ff"

    implicitWidth: 180
    implicitHeight: 180

    ShaderEffect {
        id: dial
        width: Math.min(g.width, g.height)
        height: width
        anchors.centerIn: parent
        fragmentShader: "../shaders/gauge.frag.qsb"

        property color trackColor: "#252a35"
        property color valueColor: g.accent
        property color warnColor: "#c08a18"
        property color dangerColor: "#c9343a"
        property color tickColor: "#4c5466"
        property real frac: Math.max(0, Math.min(1, (g.value - g.minimum) / g.span))
        property real warnFrac: Math.min(1, (g.warning - g.minimum) / g.span)
        property real dangerFrac: Math.min(1, (g.danger - g.minimum) / g.span)
        property real thickness: 0.12
        property real ticks: g.ticks
        property real px: 2.0 / Math.max(1, width)
    }

    Column {
        anchors.centerIn: dial
        anchors.verticalCenterOffset: dial.height * 0.03
        spacing: 0
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: g.value.toFixed(g.decimals)
            color: "#eef2f8"
            font.pixelSize: Math.max(10, dial.height * 0.22)
            font.weight: Font.DemiBold
            font.features: { "tnum": 1 }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: g.unit
            color: "#8a93a6"
            font.pixelSize: Math.max(8, dial.height * 0.085)
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            visible: g.subtitle !== ""
            text: g.subtitle
            color: "#ffb020"
            font.pixelSize: Math.max(8, dial.height * 0.075)
        }
    }

    Text {
        anchors.horizontalCenter: dial.horizontalCenter
        anchors.bottom: dial.bottom
        anchors.bottomMargin: dial.height * 0.04
        text: g.label
        color: "#c4cad6"
        font.pixelSize: Math.max(8, dial.height * 0.075)
        font.letterSpacing: 1
    }
}
