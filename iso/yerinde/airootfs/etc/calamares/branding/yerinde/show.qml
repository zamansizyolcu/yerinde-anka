import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    Rectangle {
        color: "#F7F2E2"
        anchors.fill: parent
    }

    Image {
        id: logo
        source: "yerinde-anka-lockup-720.png"
        width: 720
        height: 240
        fillMode: Image.PreserveAspectFit
        anchors.centerIn: parent
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: logo.bottom
        anchors.topMargin: 16
        color: "#1F3D2E"
        font.pointSize: 14
        text: "Yerinde ANKA kuruluyor..."
        wrapMode: Text.WordWrap
    }

    Timer {
        id: advanceTimer
        interval: 20000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    function onActivate() {
        presentation.currentSlide = 0;
    }

    function onLeave() {
    }
}
