import QtQuick

Item {
    id: g

    property string label
    property string unit
    property real value: minValue
    property real textValue: value
    property bool valid: true
    property real minValue: 0
    property real maxValue: 100
    property real warnFrom: Infinity
    property real marker: NaN
    property int decimals: 0
    property int ticks: 10
    property color fillColor: Theme.accent

    function norm(x) { return Math.max(0, Math.min(1, (x - minValue) / (maxValue - minValue))) }

    // 30 Hz de dados viram 60+ fps de movimento: a animacao so muda um uniform.
    property real shown: valid ? norm(value) : 0
    Behavior on shown { NumberAnimation { duration: 70 } }

    ShaderEffect {
        id: dial
        anchors.centerIn: parent
        width: Math.min(g.width, g.height * 1.08)
        height: width

        property real value: g.shown
        property real warnFrom: isFinite(g.warnFrom) ? g.norm(g.warnFrom) : 2.0
        property real marker: isNaN(g.marker) || !g.valid ? -1.0 : g.norm(g.marker)
        property real thickness: 0.13
        property real ticks: g.ticks
        property color trackColor: Theme.track
        property color fillColor: g.fillColor
        property color warnColor: Theme.warn
        property color markerColor: Theme.marker
        property color tickColor: Theme.tick

        fragmentShader: Qt.resolvedUrl("../shaders/arcgauge.frag.qsb")
    }

    Column {
        anchors.centerIn: dial
        anchors.verticalCenterOffset: dial.height * 0.04
        spacing: 0
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: g.valid ? g.textValue.toFixed(g.decimals) : "--"
            color: g.valid && g.textValue >= g.warnFrom ? Theme.warn : Theme.text
            font.pixelSize: dial.height * 0.2
            font.weight: Font.DemiBold
            font.family: Theme.mono
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: g.unit
            color: Theme.dim
            font.pixelSize: dial.height * 0.075
        }
    }

    Text {
        anchors.horizontalCenter: dial.horizontalCenter
        y: dial.y + dial.height * 0.8
        text: g.label
        color: Theme.label
        font.pixelSize: Math.max(11, dial.height * 0.07)
        font.weight: Font.Medium
        font.letterSpacing: 1
    }

    Text {
        x: dial.x + dial.width * 0.2 - width / 2
        y: dial.y + dial.height * 0.86
        text: g.minValue
        color: Theme.dim
        font.pixelSize: Math.max(9, dial.height * 0.05)
    }
    Text {
        x: dial.x + dial.width * 0.8 - width / 2
        y: dial.y + dial.height * 0.86
        text: g.maxValue
        color: Theme.dim
        font.pixelSize: Math.max(9, dial.height * 0.05)
    }
}
