import QtQuick 2.11
import SddmComponents 2.0

Rectangle {
    id: container
    width: Screen.width
    height: Screen.height
    color: "#F7F2E2"

    // final15.md §2c: Oturum seçimi GERÇEKTEN işlesin.
    // SDDM 0.21.0'da `session` bağlam nesnesi YOKTUR (yalnızca sessionModel).
    // İlk seçim = sessionModel.lastIndex (önceki oturum; ilk açılışta 0).
    // ComboBox seçimi değişince sessionIndex güncellenir ve sddm.login'e
    // aktarılır (X11 seçilince X11 açılır; eskiden hep Wayland başlardı).
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

        TextBox {
            id: userEntry
            width: 260
            height: 32
            text: userModel.lastUser
            KeyNavigation.tab: passwordEntry
            Keys.onReturnPressed: loginButton.onClicked()
            Keys.onEnterPressed: loginButton.onClicked()
        }

        PasswordBox {
            id: passwordEntry
            width: 260
            height: 32
            focus: true
            KeyNavigation.tab: sessionCombo
            Keys.onReturnPressed: loginButton.onClicked()
            Keys.onEnterPressed: loginButton.onClicked()
        }

        // final16.md §1: Oturum seçici + Giriş + ⟳ + ⏻ TEK satırda (Row), ortalanmış.
        Row {
            spacing: 8
            anchors.horizontalCenter: parent.horizontalCenter

            // final19.md §2: tek oturum (Wayland) seçici + etiket gizlenir;
            // düzen bozulmasın. sessionModel.count > 1 ise tekrar görünür.
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
                index: sessionIndex
                onValueChanged: sessionIndex = index
                KeyNavigation.tab: loginButton
                visible: sessionModel.count > 1
            }

            Button {
                id: loginButton
                width: 180
                height: 36
                text: "Giriş"
                onClicked: sddm.login(userEntry.text, passwordEntry.text, sessionIndex)
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

    Component.onCompleted: {
        passwordEntry.forceActiveFocus()
        sddm.state = "login"
    }
}
