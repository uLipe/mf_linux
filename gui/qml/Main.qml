import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1480
    height: 920
    visible: true
    title: "MasterFuel Linux" + (backend.signature ? " — " + backend.signature : "")
    color: "#12151b"
    Material.theme: Material.Dark
    Material.accent: "#39c0ff"

    header: ToolBar {
        Material.background: "#181c24"
        RowLayout {
            anchors.fill: parent
            anchors.rightMargin: 12
            TabBar {
                id: tabs
                currentIndex: initialTab
                Material.background: "transparent"
                TabButton { text: "Painel"; width: 120 }
                TabButton { text: "Mapas"; width: 120 }
            }
            Item { Layout.fillWidth: true }
            Label {
                visible: backend.unburned > 0
                text: backend.unburned + (backend.unburned === 1 ? " página alterada" : " páginas alteradas")
                      + " só na RAM"
                color: "#ffb020"
            }
            Button {
                text: "Gravar na flash"
                enabled: backend.connected && backend.unburned > 0
                highlighted: enabled
                onClicked: burnDialog.open()
            }
        }
    }

    StackLayout {
        anchors.fill: parent
        currentIndex: tabs.currentIndex
        Dashboard {}
        TuneView {}
    }

    footer: Rectangle {
        height: 26
        color: "#181c24"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 16
            Rectangle {
                width: 10; height: 10; radius: 5
                color: backend.connected ? "#7ee081" : "#ff5a5f"
            }
            Label { text: backend.status; color: "#aab2c2"; font.pixelSize: 12 }
            Label {
                visible: backend.connected
                text: backend.liveHz.toFixed(0) + " quadros/s"
                color: "#aab2c2"; font.pixelSize: 12
            }
            Label {
                visible: backend.connected
                text: "sync loss " + (backend.live.syncLoss || 0)
                color: (backend.live.syncLoss || 0) > 0 ? "#ffb020" : "#aab2c2"
                font.pixelSize: 12
            }
            Item { Layout.fillWidth: true }
            Label { text: backend.renderer; color: "#6c7486"; font.pixelSize: 12 }
        }
    }

    Dialog {
        id: burnDialog
        anchors.centerIn: parent
        modal: true
        title: "Gravar na flash da ECU?"
        standardButtons: Dialog.Yes | Dialog.Cancel
        Label {
            text: "As alterações feitas nesta sessão passam a valer\ndepois de desligar a ECU."
        }
        onAccepted: backend.burn()
    }

    Rectangle {
        id: toast
        property alias text: toastText.text
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        width: toastText.implicitWidth + 32
        height: 40
        radius: 8
        color: "#3a1d20"
        border.color: "#ff5a5f"
        opacity: 0
        Behavior on opacity { NumberAnimation { duration: 200 } }
        Label { id: toastText; anchors.centerIn: parent; color: "#ffd6d8" }
        Timer { id: toastTimer; interval: 5000; onTriggered: toast.opacity = 0 }
    }

    Connections {
        target: backend
        function onErrorOccurred(msg) {
            toast.text = msg
            toast.opacity = 1
            toastTimer.restart()
        }
    }
}
