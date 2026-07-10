import os
from app import create_app

# Cria a instância da aplicação Flask
# Esta variável 'app' é a que será utilizada pelo Gunicorn em produção (ex: gunicorn app:app)
app = create_app()

if __name__ == '__main__':
    # No Railway, Render ou Heroku, a porta é injetada via variável de ambiente $PORT.
    # O host '0.0.0.0' é obrigatório para que a aplicação aceite conexões externas e não fique restrita ao localhost.
    port = int(os.environ.get("PORT", 80))
    
    # Debug=False é crucial para ambientes de produção por motivos de segurança e performance.
    app.run(host='0.0.0.0', port=port, debug=False)
