/* =====================================================================
   Mapa para marcar um local: a casa do usuário ou uma nova máquina.

   Usa MapLibre GL JS (biblioteca do mapa) + OpenFreeMap (imagens do mapa),
   gratuitos e sem chave. Funciona em qualquer formulário que tenha:
     - um <div data-mapa-escolha> (onde o mapa é desenhado);
     - campos name="lat" e name="lng" (preenchidos ao clicar no mapa);
     - opcional: botão [data-localizar] + campos de endereço (busca no Nominatim);
     - opcional: campo [data-cep] (preenche rua, bairro, cidade e UF pelo ViaCEP).
   Sem internet o mapa não aparece, mas dá para digitar latitude e longitude.
   Este arquivo é só ajuda visual: quem valida os dados é o model, no servidor.
   ===================================================================== */
(function () {
  const CENTRO_SAO_PAULO = [-46.6333, -23.5505];   // o MapLibre usa [longitude, latitude]
  const ESTILO_MAPA = 'https://tiles.openfreemap.org/styles/positron';
  const CAMPOS_DO_ENDERECO = ['cep', 'logradouro', 'numero', 'bairro', 'cidade', 'uf'];

  // Liga o mapa e o CEP em cada formulário da página que tiver esses elementos
  document.querySelectorAll('form').forEach(form => {
    const caixa = form.querySelector('[data-mapa-escolha]');
    if (caixa) iniciarMapa(form, caixa);
    const cep = form.querySelector('[data-cep]');
    if (cep) iniciarCep(form, cep);
  });

  /** Converte o texto do campo em número (aceita vírgula). Devolve null se não for número. */
  function numero(texto) {
    const n = parseFloat(String(texto).replace(',', '.'));
    return Number.isFinite(n) ? n : null;
  }

  /** Cria um pino colorido no mapa, com o nome aparecendo ao clicar nele. */
  function criarPino(mapa, lat, lng, cor, titulo, arrastavel = false) {
    const pino = new maplibregl.Marker({color: cor, draggable: arrastavel})
      .setLngLat([lng, lat])
      .setPopup(new maplibregl.Popup({offset: 28, closeButton: false}).setText(titulo))
      .addTo(mapa);
    pino.getElement().title = titulo;
    return pino;
  }

  /** Desenha o mapa do formulário e liga: clique no mapa, arrasto do pino e campos lat/lng. */
  function iniciarMapa(form, caixa) {
    const campoLat = form.elements.lat, campoLng = form.elements.lng;
    const info = form.querySelector('[data-mapa-info]');
    const cor = caixa.dataset.corPino || '#1a73e8';
    const rotulo = caixa.dataset.rotuloPino || 'Local';
    if (!window.maplibregl) {
      caixa.innerHTML = '<div class="mapa-vazio">Mapa indisponível (sem internet?). Digite a latitude e a longitude abaixo.</div>';
      return;
    }

    const mapa = new maplibregl.Map({container: caixa, style: ESTILO_MAPA, center: CENTRO_SAO_PAULO,
                                     zoom: 10.5, attributionControl: {compact: true}});
    mapa.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right');
    // pinos verdes das máquinas que já existem (a central do admin manda a lista em data-pinos)
    JSON.parse(caixa.dataset.pinos || '[]').forEach(m => criarPino(mapa, m.lat, m.lng, '#2fb24c', m.nome));

    let pino = null;

    /** Põe o pino em (lat, lng), escreve os valores nos campos e, se pedido, centraliza o mapa. */
    function marcar(lat, lng, centralizar) {
      campoLat.value = lat.toFixed(6);
      campoLng.value = lng.toFixed(6);
      if (!pino) {
        pino = criarPino(mapa, lat, lng, cor, rotulo, true);
        pino.on('dragend', () => { const p = pino.getLngLat(); marcar(p.lat, p.lng, false); });
      } else {
        pino.setLngLat([lng, lat]);
      }
      if (info) info.textContent = `${rotulo}: ${lat.toFixed(5)}, ${lng.toFixed(5)}. Se não estiver certo, clique no mapa ou arraste o pino.`;
      if (centralizar) mapa.jumpTo({center: [lng, lat], zoom: Math.max(mapa.getZoom(), 15)});
    }

    /** Apaga o pino e as coordenadas (o endereço mudou, então o local antigo não vale mais). */
    function limpar() {
      pino?.remove();
      pino = null;
      campoLat.value = campoLng.value = '';
      if (info) info.textContent = 'O endereço mudou: clique em "Localizar endereço no mapa" de novo ou marque o local no mapa.';
    }

    mapa.on('click', e => marcar(e.lngLat.lat, e.lngLat.lng, false));
    // digitou as coordenadas na mão: o pino vai até elas
    [campoLat, campoLng].forEach(campo => campo.addEventListener('change', () => {
      const lat = numero(campoLat.value), lng = numero(campoLng.value);
      if (lat !== null && lng !== null) marcar(lat, lng, true);
    }));
    // o formulário já veio com coordenadas (alterar endereço ou erro no envio): mostra o pino
    const lat0 = numero(campoLat.value), lng0 = numero(campoLng.value);
    if (lat0 !== null && lng0 !== null) mapa.once('load', () => marcar(lat0, lng0, true));

    const botao = form.querySelector('[data-localizar]');
    if (!botao) return;
    botao.addEventListener('click', () => localizar(form, marcar, info));
    CAMPOS_DO_ENDERECO.forEach(nome => form.elements[nome]?.addEventListener('change', limpar));
    form.addEventListener('endereco-preenchido', limpar);   // aviso do preenchimento pelo CEP
  }

  /** Nominatim (OpenStreetMap): transforma endereço em latitude/longitude. Grátis, 1 consulta por segundo. */
  async function nominatim(parametros) {
    const consulta = new URLSearchParams({format: 'jsonv2', limit: '1', countrycodes: 'br',
                                          'accept-language': 'pt-BR', ...parametros});
    const resposta = await fetch('https://nominatim.openstreetmap.org/search?' + consulta);
    if (!resposta.ok) throw new Error('falha no Nominatim');
    return (await resposta.json())[0];
  }

  /** Botão "Localizar endereço no mapa": procura rua + número; se não achar, só a rua. */
  async function localizar(form, marcar, info) {
    const valor = nome => (form.elements[nome]?.value || '').trim();
    const faltando = ['logradouro', 'numero', 'cidade', 'uf'].find(nome => !valor(nome));
    if (faltando) { form.elements[faltando].reportValidity(); return; }
    info.textContent = 'Procurando o endereço…';
    try {
      let achou = await nominatim({street: `${valor('numero')} ${valor('logradouro')}`, city: valor('cidade'),
                                   state: valor('uf'), postalcode: valor('cep')});
      const exato = !!achou;
      if (!achou) achou = await nominatim({street: valor('logradouro'), city: valor('cidade'), state: valor('uf')});
      if (!achou) {
        info.textContent = 'Não encontramos esse endereço. Confira os dados ou clique no mapa para marcar a sua casa.';
        return;
      }
      marcar(Number(achou.lat), Number(achou.lon), true);
      if (!exato) info.textContent = 'Achamos a rua, mas não o número. Arraste o pino até a sua casa.';
    } catch {
      info.textContent = 'Não foi possível localizar agora. Clique no mapa ou digite latitude e longitude.';
    }
  }

  /** Campo CEP: põe o traço (00000-000) e, com 8 dígitos, busca rua, bairro, cidade e UF no ViaCEP. */
  function iniciarCep(form, campo) {
    campo.addEventListener('input', async () => {
      const digitos = campo.value.replace(/\D/g, '').slice(0, 8);
      campo.value = digitos.length > 5 ? `${digitos.slice(0, 5)}-${digitos.slice(5)}` : digitos;
      if (digitos.length !== 8) return;
      try {
        const r = await (await fetch(`https://viacep.com.br/ws/${digitos}/json/`)).json();
        if (r.erro) return;
        if (r.logradouro) form.elements.logradouro.value = r.logradouro;
        if (r.bairro) form.elements.bairro.value = r.bairro;
        form.elements.cidade.value = r.localidade || '';
        form.elements.uf.value = r.uf || '';
        form.dispatchEvent(new Event('endereco-preenchido'));
        form.elements.numero.focus();
      } catch {
        // sem internet: a pessoa preenche o endereço à mão
      }
    });
  }
})();
