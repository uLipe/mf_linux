import QtQuick
import QtGraphs

Rectangle {
    id: chart

    property string title
    property real yMin: 0
    property real yMax: 100
    property real yTick: (yMax - yMin) / 4
    property real span: 10
    property string key1
    property string key2
    property string name1
    property string name2
    property color color1: Theme.accent
    property color color2: Theme.marker

    color: Theme.panel
    radius: 6
    border.color: Theme.border

    function push(v) {
        const t = v._t
        add(s1, t, v[key1])
        if (key2)
            add(s2, t, v[key2])
        ax.min = t - span
        ax.max = t
    }

    function add(series, t, y) {
        if (y === undefined)
            return
        series.append(t, y)
        let old = 0
        while (old < series.count && series.at(old).x < t - span - 0.5)
            old++
        if (old > 0)
            series.removeMultiple(0, old)
    }

    Row {
        x: 12; y: 6
        spacing: 14
        Text { text: chart.title; color: Theme.label; font.pixelSize: 12; font.weight: Font.Medium }
        Text { text: "\u25CF " + chart.name1; color: chart.color1; font.pixelSize: 11; visible: chart.name1 !== "" }
        Text { text: "\u25CF " + chart.name2; color: chart.color2; font.pixelSize: 11; visible: chart.key2 !== "" }
    }

    GraphsView {
        anchors.fill: parent
        anchors.topMargin: 22
        marginLeft: 4; marginRight: 10; marginTop: 4; marginBottom: 2

        theme: GraphsTheme {
            colorScheme: GraphsTheme.ColorScheme.Dark
            backgroundVisible: false
            plotAreaBackgroundColor: Theme.panel
            grid.mainColor: Theme.border
            grid.subColor: "transparent"
            axisX.mainColor: Theme.border
            axisY.mainColor: Theme.border
            labelTextColor: Theme.dim
            axisYLabelFont.pixelSize: 10
        }

        axisX: ValueAxis {
            id: ax
            min: -chart.span
            max: 0
            labelsVisible: false
            tickInterval: 1
        }
        axisY: ValueAxis {
            min: chart.yMin
            max: chart.yMax
            tickInterval: chart.yTick
            labelDecimals: 0
        }

        LineSeries { id: s1; color: chart.color1; width: 2 }
        LineSeries { id: s2; color: chart.color2; width: 1.5; visible: chart.key2 !== "" }
    }
}
