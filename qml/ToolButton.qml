import QtQuick

Rectangle {
    id: btn
    property string text
    property bool active: true
    property bool accent: false
    signal clicked
    implicitWidth: lbl.implicitWidth + 22
    implicitHeight: 28
    radius: 5
    color: accent ? Theme.marker : (area.containsMouse && active ? Theme.tick : Theme.track)
    opacity: active ? 1 : 0.4
    Text {
        id: lbl
        anchors.centerIn: parent
        text: btn.text
        color: btn.accent ? Theme.bg : Theme.text
        font.pixelSize: 12
        font.weight: btn.accent ? Font.DemiBold : Font.Normal
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: if (btn.active) btn.clicked()
    }
}
