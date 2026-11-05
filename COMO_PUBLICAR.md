# Como publicar no GitHub (Windows / PowerShell)

## 0. Pré-requisitos (só uma vez)
1. Crie sua conta em https://github.com (use um e-mail pessoal, não o da Mantis).
2. Instale o Git: `winget install --id Git.Git -e`
3. Configure seu nome:
   ```powershell
   git config --global user.name "André Casemiro"
   git config --global user.email "SEU_EMAIL_DO_GITHUB"
   ```

## 1. README de perfil (aparece na sua página principal)
1. No GitHub, crie um repositório **com exatamente o mesmo nome do seu usuário** (ex.: `andrecasemiro/andrecasemiro`), público, marcando "Add a README file".
2. Edite o README pelo navegador e cole o conteúdo de `perfil-github/README.md`.
3. Troque `<seu-usuario>`, `<seu-linkedin>` e `<seu-email-pessoal>` pelos seus dados.

## 2. Projeto de scouting
1. No GitHub, crie um repositório **vazio** chamado `scouting-futebol` (público, sem README).
2. Descompacte o zip, entre na pasta e rode:
   ```powershell
   cd scouting-futebol
   git init
   git add .
   git commit -m "Projeto de scouting por similaridade com StatsBomb Open Data"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/scouting-futebol.git
   git push -u origin main
   ```
3. No README do projeto, troque `<seu-usuario>` e `<seu-linkedin>`.
4. Na página do repositório, clique na engrenagem ao lado de **About** e adicione:
   - Descrição: *Scouting de jogadores por similaridade estatística com StatsBomb Open Data*
   - Tópicos: `football-analytics` `scouting` `python` `statsbomb` `data-science` `soccer`

## 3. Rodar no seu computador (opcional)
```powershell
cd scouting-futebol
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.features
jupyter notebook notebooks\01_scouting_similaridade.ipynb
```

## 4. Divulgar
Poste no LinkedIn a pizza do Vini e a tabela de similares, com o link do repositório. Marque com #footballanalytics e #datascience.
