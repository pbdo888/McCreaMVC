/* =====================================================================
   Mapa do painel do Perfil: da casa do usuário até a máquina mais próxima.

   Mesma ideia do mapa do projeto completo:
     - pino azul = a casa; pinos verdes = as máquinas;
     - linha tracejada ligando a casa à máquina mais próxima (linha reta,
       a mesma distância que o model calculou, não uma rota de ruas);
     - o mapa já abre enquadrando a casa e a máquina; segue o tema claro/escuro.

   Usa MapLibre GL JS + OpenFreeMap, gratuitos e sem chave. Os dados vêm
   prontos do servidor (Usuario.dados_do_mapa), no atributo data-mapa-casa
   do <div>: este arquivo só desenha, não calcula nem decide nada.
   ===================================================================== */
(function () {
  const caixa = document.querySelector('[data-mapa-casa]');
  if (!caixa) return;   // esta página não tem o mapa
  const dados = JSON.parse(caixa.dataset.mapaCasa);   // {casa, maquinas, proxima}

  const COR_CASA = '#1a73e8';       // azul, igual à legenda
  const COR_MAQUINA = '#2fb24c';    // verde, igual à legenda
  const COR_LINHA = '#1aa3e8';
  const temaEscuro = window.matchMedia('(prefers-color-scheme: dark)');

  if (!window.maplibregl) {
    caixa.innerHTML = '<div class="mapa-vazio">Não foi possível carregar o mapa. Verifique sua conexão com a internet.</div>';
    return;
  }
  iniciarMapa();

  /** Endereço do estilo do mapa: claro ("positron") ou escuro, conforme o tema do sistema. */
  function estiloMapa() {
    return `https://tiles.openfreemap.org/styles/${temaEscuro.matches ? 'dark' : 'positron'}`;
  }

  /** Cria um pino colorido; ao clicar nele aparece o texto `titulo`. */
  function criarPino(mapa, pos, cor, titulo) {
    const pino = new maplibregl.Marker({color: cor})
      .setLngLat([pos.lng, pos.lat])   // o MapLibre usa [longitude, latitude]
      .setPopup(new maplibregl.Popup({offset: 28, closeButton: false}).setText(titulo))
      .addTo(mapa);
    pino.getElement().title = titulo;
    return pino;
  }

  /** Coordenadas da linha reta casa → máquina mais próxima (vazia se não houver máquina). */
  function coordenadasDaLinha() {
    if (!dados.proxima) return [];
    return [[dados.casa.lng, dados.casa.lat], [dados.proxima.lng, dados.proxima.lat]];
  }

  /** Coloca no mapa a camada da linha tracejada (precisa ser refeita se o estilo do mapa trocar). */
  function desenharLinha(mapa) {
    if (mapa.getSource('rota')) return;
    mapa.addSource('rota', {type: 'geojson', data: {
      type: 'Feature', properties: {}, geometry: {type: 'LineString', coordinates: coordenadasDaLinha()}}});
    mapa.addLayer({id: 'rota', type: 'line', source: 'rota', layout: {'line-cap': 'round'},
                   paint: {'line-color': COR_LINHA, 'line-width': 4, 'line-dasharray': [1, 2]}});
  }

  /** Retângulo que contém a casa e a máquina mais próxima, para o mapa já abrir enquadrando os dois. */
  function limitesIniciais() {
    const pontos = [dados.casa, dados.proxima || dados.casa];
    const lngs = pontos.map(p => p.lng), lats = pontos.map(p => p.lat);
    return [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]];
  }

  /** Cria o mapa, os pinos, os botões de zoom/tela cheia e a linha tracejada. */
  function iniciarMapa() {
    caixa.innerHTML = '';   // tira o aviso "Carregando o mapa…" que veio no HTML
    const mapa = new maplibregl.Map({
      container: caixa, style: estiloMapa(), attributionControl: {compact: true},
      bounds: limitesIniciais(), fitBoundsOptions: {padding: 70, maxZoom: 15}});
    mapa.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right');
    mapa.addControl(new maplibregl.FullscreenControl(), 'top-right');

    criarPino(mapa, dados.casa, COR_CASA, dados.casa.nome);
    dados.maquinas.forEach(m => {
      const maisProxima = dados.proxima && m.lat === dados.proxima.lat && m.lng === dados.proxima.lng;
      const titulo = maisProxima
        ? `${m.nome} · mais próxima (${dados.proxima.km.toFixed(2).replace('.', ',')} km)` : m.nome;
      criarPino(mapa, m, COR_MAQUINA, titulo);
    });

    // a linha é refeita sempre que um estilo termina de carregar (inclusive na troca claro/escuro)
    mapa.on('style.load', () => desenharLinha(mapa));
    temaEscuro.addEventListener('change', () => mapa.setStyle(estiloMapa()));
    mapa.on('error', e => console.warn('Mapa:', e.error?.message || e));
  }
})();
