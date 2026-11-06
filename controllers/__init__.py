"""
C de MVC: os CONTROLLERS.

Cada controller é um Blueprint do Flask com as rotas (URLs) de uma aba:

    perfil_controller.py  ->  /perfil/...  (aba Perfil)
    admin_controller.py   ->  /admin/...   (aba Admin)

O papel do controller é só coordenar: recebe a requisição do navegador, chama
os models para fazer o trabalho e escolhe qual view (template HTML) mostrar,
passando os dados para ela. As regras de negócio ficam nos models.
"""
