# Envio de Boletos

Uma aplicação web desenvolvida em **Python** e **Streamlit** criada para facilitar a automação e disparo de e-mails contendo boletos bancários em PDF para clientes. O sistema cruza os dados de uma planilha Excel com os arquivos PDF nomeados com o respectivo CNPJ e realiza o envio seguro de e-mails em lote.

## 🚀 Funcionalidades

- **Acesso Restrito:** Autenticação por senha para garantir a segurança da operação.
- **Upload Simplificado:** 
  - Suporta planilha principal no formato Excel (`.xlsx` ou `.xls`).
  - Upload em lote (múltiplos arquivos) de boletos bancários em formato `.pdf`.
- **Cruzamento de Dados Automático:** Associa cada cliente da planilha ao seu respectivo PDF através do CNPJ.
- **Parametrização do E-mail:** Template dinâmico e editável para o assunto e o corpo do e-mail com variáveis suportadas como `{nome}`, `{razao_social}` e `{cnpj}`.
- **Múltiplos Remetentes:** Seleção na interface para definir qual e-mail configurado será o remetente do lote, útil para o caso de diferentes setores ou empresas no mesmo sistema.
- **Controle de Envio Inteligente:** Mostra quais arquivos têm nomes inválidos, CNPJs duplicados ou e-mails vazios. Pausa estrategicamente 3 segundos entre cada disparo para evitar bloqueios de provedores SMTP.

## 📋 Pré-requisitos

Para rodar o projeto localmente, certifique-se de possuir o **Python 3.8+** instalado em seu sistema.

As bibliotecas necessárias podem ser verificadas pelo que é importado na aplicação:
- `streamlit`
- `pandas`
- `openpyxl` (Necessário no pandas para leitura de arquivos `.xlsx`)

## 🛠️ Instalação e Configuração

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/Joaocruz1999/envioboletos.git
   cd envioboletos
   ```

2. **Crie e ative um ambiente virtual (Opcional, mas recomendado):**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux / Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install streamlit pandas openpyxl
   ```

4. **Configuração de Variáveis (Secrets do Streamlit):**
   O projeto requer um arquivo de configuração TOML onde ficarão as senhas de acesso e as credenciais de SMTP.
   - Crie um diretório chamado `.streamlit` na raiz do projeto.
   - Dentro dessa pasta, crie um arquivo chamado `secrets.toml`.
   - Utilize a estrutura exemplificada no `.env.example` da raiz, substituindo para os seus dados reais:

   *Exemplo de `secrets.toml`:*
   ```toml
   [app]
   access_password = "senha_de_acesso_para_entrar_no_app"

   [smtp]
   host = "smtp.gmail.com"
   port = 587

   [senders.financeiro]
   email = "financeiro@suaempresa.com.br"
   app_password = "sua_senha_de_aplicativo_do_email"
   display_name = "Financeiro - Sua Empresa"
   ```

## 🖥️ Como Usar (Uso e Arquivos Esperados)

1. **Inicialize a aplicação:**
   ```bash
   streamlit run app.py
   ```

2. **Acesse via Navegador:** 
   O terminal fornecerá uma URL local (normalmente `http://localhost:8501`). Acesse-a, digite a sua `access_password` configurada no arquivo `secrets.toml` e inicie.

3. **Arquivos Esperados no Upload:**
   - **Planilha Excel:** 
     Obrigatório conter as seguintes colunas nomeadas exatamente dessa maneira (case-sensitive não é totalmente exigido exceto pela checagem exata, mantenha simples): `Nome`, `Razao Social`, `CNPJ` e `Email`. 
     *Atenção: A coluna CNPJ deve ter preenchimento de clientes válidos.*
   - **Arquivos PDF:** 
     Todos os boletos **devem** estar numerados com a seguinte regra e prefixo: `boleto_{UM_CNPJ_DE_14_DIGITOS}.pdf`. 
     *Exemplo correto:* `boleto_01234567890123.pdf`.
     
4. **Processamento e Disparo:** Clique em "Processar uploads" para gerar o cruzamento de todos os itens e verifique a tabela resultante na tela. Selecione quem deseja notificar e, ao clicar em "Disparar E-mails", as cópias serão enviadas instantaneamente e os arquivos temporários criados nos servidos serão apagados após o término no intuito de poupar armazenamento.

---

> Desenvolvido para agilizar as operações financeiras no envio massivo de faturas e boletos mensais.
