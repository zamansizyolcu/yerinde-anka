
// Single-language bootloader.
(function() {
  // Application path.
  var appName = location.pathname.match(/\/([-\w]+)(\.html)?$/);
  appName = appName ? appName[1].replace('-', '/') : 'index';

  // Only one language.
  var lang = 'tr';
  window['BlocklyGamesLanguages'] = [lang];
  window['BlocklyGamesLang'] = lang;

  // Load the language pack.
  var script = document.createElement('script');
  script.src = appName + '/generated/' + lang + '/compressed.js';
  script.type = 'text/javascript';
  document.head.appendChild(script);
})();

/* ---------- YERİNDE sesli kapatma köprüsü ---------- */
(function(){
  function connect(){
    try {
      var ws = new WebSocket("ws://127.0.0.1:8765/");
      ws.onmessage = function(ev){
        try {
          var cmd = JSON.parse(ev.data);
          if (cmd && cmd.action === "close_tool") { window.close(); }
        } catch(e) {}
      };
      ws.onclose = function(){ setTimeout(connect, 2500); };
      ws.onerror = function(){ try{ ws.close(); }catch(e){} };
    } catch(e) {
      setTimeout(connect, 2500);
    }
  }
  connect();
})();
