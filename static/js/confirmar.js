/* Pede confirmação antes de enviar formulários marcados com data-confirmar
   (ex.: excluir um anúncio). Se a pessoa clicar em "Cancelar", nada é enviado. */
document.addEventListener('submit', evento => {
  const pergunta = evento.target.dataset.confirmar;
  if (pergunta && !confirm(pergunta)) evento.preventDefault();
});
