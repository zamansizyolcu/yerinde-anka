import QtQuick 2.11
import SddmComponents 2.0

Rectangle {
    id: container
    width: Screen.width
    height: Screen.height
    color: "#F7F2E2"

    property int sessionIndex: sessionModel.lastIndex

    Connections {
        target: sddm
        onLoginFailed: {
            passwordEntry.text = ""
            messageText.text = "Hatalı kullanıcı adı veya parola."
            messageText.visible = true
        }
    }

    Image {
        id: logo
        source: "yerinde-anka-lockup-720.png"
        width: 720
        height: 240
        fillMode: Image.PreserveAspectFit
        anchors.top: parent.top
        anchors.topMargin: parent.height * 0.12
        anchors.horizontalCenter: parent.horizontalCenter
    }

    Text {
        id: messageText
        anchors.top: logo.bottom
        anchors.topMargin: 24
        anchors.horizontalCenter: parent.horizontalCenter
        text: ""
        visible: false
        color: "#C64A17"
        font.pointSize: 11
    }

    Column {
        anchors.centerIn: parent
        spacing: 12

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Yerinde ANKA"
            color: "#1F3D2E"
            font.pointSize: 20
            font.bold: true
        }

        // final56: Saf QtQuick ListView — kullanıcı listesi (Controls YASAK)
        ListView {
            id: userListView
            model: userModel
            currentIndex: userModel.lastIndex
            width: 260; height: Math.min(contentHeight, 220)
            interactive: contentHeight > height
            delegate: Rectangle {
                property string userName: model.name
                width: userListView.width; height: 44; radius: 6
                color: userListView.currentIndex === index ? "#C74A1F" : "#EFE9DC"
                border.color: "#0B3D2E"; border.width: 1
                Text { anchors.centerIn: parent
                       text: model.realName !== "" ? model.realName : model.name
                       color: userListView.currentIndex === index ? "#FFFFFF" : "#0B3D2E"
                       font.pixelSize: 15 }
                MouseArea { anchors.fill: parent
                            onClicked: userListView.currentIndex = index }
            }
        }

        // Parola girişi — SddmComponents PasswordBox
        PasswordBox {
            id: passwordEntry
            width: 260
            height: 32
            focus: true
            KeyNavigation.tab: sessionCombo
            Keys.onReturnPressed: loginButton.onClicked()
            Keys.onEnterPressed: loginButton.onClicked()
        }

        // Oturum seçici + Giriş + ⟳ + ＋ + ⏻ — tek satırda (Row)
        Row {
            spacing: 8
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                text: "Oturum:"
                color: "#1F3D2E"
                font.pointSize: 11
                anchors.verticalCenter: parent.verticalCenter
                visible: sessionModel.count > 1
            }

            ComboBox {
                id: sessionCombo
                width: 220
                height: 28
                model: sessionModel
                onValueChanged: sessionIndex = index
                KeyNavigation.tab: loginButton
                visible: sessionModel.count > 1
            }

            Button {
                id: loginButton
                width: 180
                height: 36
                text: "Giriş"
                onClicked: sddm.login(userListView.currentItem.userName, passwordEntry.text, sessionIndex)
                KeyNavigation.backtab: sessionCombo
            }

            Button {
                id: rebootButton
                width: 36
                height: 36
                text: "⟳"
                visible: sddm.canReboot
                onClicked: sddm.reboot()
            }

            // ＋ YENİ KULLANICI — bilgi penceresi
            Button {
                id: addUserButton
                width: 36
                height: 36
                text: "＋"
                onClicked: infoDialog.visible = true
            }

            Button {
                id: powerOffButton
                width: 36
                height: 36
                text: "⏻"
                visible: sddm.canPowerOff
                onClicked: sddm.powerOff()
            }
        }
    }

    // Bilgi penceresi
    Rectangle {
        id: infoDialog
        visible: false
        anchors.centerIn: parent
        width: 380
        height: 160
        color: "#F7F2E2"
        border.color: "#1F3D2E"
        border.width: 2
        radius: 8
        z: 100

        Column {
            anchors.centerIn: parent
            spacing: 16
            width: parent.width - 32

            Text {
                text: "Yeni Kullanıcı Ekleme"
                color: "#1F3D2E"
                font.pointSize: 14
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Text {
                text: "Yeni kullanıcı eklemek için giriş yaptıktan sonra:\n\n• Yerinde Kullanıcı Yöneticisi\n  veya\n• Sistem Ayarları → Kullanıcılar"
                color: "#1F3D2E"
                font.pointSize: 11
                wrapMode: Text.WordWrap
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
            }

            Button {
                text: "Tamam"
                width: 100
                height: 32
                anchors.horizontalCenter: parent.horizontalCenter
                onClicked: infoDialog.visible = false
            }
        }
    }

    Component.onCompleted: {
        passwordEntry.forceActiveFocus()
        sddm.state = "login"
    }
}
