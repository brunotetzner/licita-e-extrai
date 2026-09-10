# licita-e-extrai

API simples em Flask com um endpoint de exemplo `GET /hello`.

## Estrutura do projeto

```text
.
├── app.py                          # Fábrica da aplicação Flask (create_app)
├── controllers/
│   ├── __init__.py
│   └── hello_controller.py         # Blueprint com o endpoint GET /hello
├── requirements.txt                # Dependências do projeto
├── README.md
└── .venv/                          # Ambiente virtual Python (não versionar)
```

## Requisitos

* Python 3.9 ou superior
* pip

## Como rodar a aplicação

### 1. Clonar o repositório

```bash
git clone https://github.com/brunotetzner/licita-e-extrai.git
cd licita-e-extrai
```

### 2. Criar o ambiente virtual

Linux / macOS:

```bash
python3 -m venv .venv
```

Windows (PowerShell):

```powershell
python -m venv .venv
```

### 3. Ativar o ambiente virtual

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Após a ativação, o terminal deverá exibir `.venv` no início da linha:

```text
(.venv) usuario@ubuntu:~/licita-e-extrai$
```

### 4. Instalar as dependências

Com o ambiente virtual ativado:

```bash
pip install -r requirements.txt
```

### 5. Iniciar o servidor

```bash
python app.py
```

O servidor será iniciado em modo de desenvolvimento em:

`http://localhost:5000`

### 6. Desativar o ambiente virtual

Quando terminar de trabalhar no projeto:

```bash
deactivate
```

Para trabalhar novamente no projeto, basta ativar o ambiente:

```bash
source .venv/bin/activate
```

## Testando o endpoint

Com o servidor em execução:

```bash
curl http://localhost:5000/hello
```

Resposta esperada:

```json
{
  "message": "Hello, World!"
}
```

## Configuração

A porta e o host podem ser alterados no bloco final de `app.py`:

```python
app.run(host="0.0.0.0", port=5000, debug=True)
```

> Em produção, não use o servidor embutido do Flask. Prefira um servidor WSGI, como o Gunicorn:
>
> ```bash
> gunicorn "app:create_app()"
> ```

## Desenvolvimento

O diretório `.venv` contém o ambiente virtual local do projeto e não deve ser versionado no Git.

Adicione ao `.gitignore`:

```gitignore
.venv/
```
