import QtQuick
import QtGraphs

// Janela deslizante dos ultimos `seconds` segundos de um canal (e, opcional, de um segundo
// canal de referencia, como o alvo de AFR).
Rectangle {
    id: chart

    property string title
    property string key
    property string refKey
    property real minimum: 0
    property real maximum: 100
    property real seconds: 20
    property color lineColor: "#39c0ff"
    property int maxPoints: seconds * 70

    readonly property real t0: Date.now()

    color: "#171b23"
    radius: 6

    Text {
        x: 10; y: 6
        text: chart.title
        color: "#8a93a6"
        font.pixelSize: 12
        font.letterSpacing: 1
    }

    GraphsView {
        id: view
        anchors.fill: parent
        anchors.topMargin: 18
        theme: GraphsTheme {
            colorScheme: GraphsTheme.ColorScheme.Dark
            backgroundVisible: false
            plotAreaBackgroundColor: "transparent"
            gridVisible: true
        }
        axisX: ValueAxis {
            id: ax
            min: -chart.seconds
            max: 0
            labelsVisible: false
            gridVisible: false
        }
        axisY: ValueAxis {
            min: chart.minimum
            max: chart.maximum
            tickInterval: (chart.maximum - chart.minimum) / 4
            labelDecimals: 0
        }
        LineSeries { id: ref; color: "#ffb020"; width: 1.5; visible: chart.refKey !== "" }
        LineSeries { id: line; color: chart.lineColor; width: 2 }
    }

    function push(series, t, v) {
        series.append(t, v)
        if (series.count > maxPoints)
            series.remove(0)
    }

    Connections {
        target: backend
        function onLiveChanged() {
            if (!chart.visible)
                return
            var t = (Date.now() - chart.t0) / 1000
            var v = backend.live
            chart.push(line, t, v[chart.key])
            if (chart.refKey !== "")
                chart.push(ref, t, v[chart.refKey])
            ax.min = t - chart.seconds
            ax.max = t
        }
    }
}
