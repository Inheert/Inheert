<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/header-light.svg">
  <img alt="Théo Claereboudt, aka Inheert, backend and infrastructure developer" src="assets/generated/header-dark.svg" width="100%">
</picture>

<a href="https://www.theocldt.dev/"><img alt="Portfolio" src="https://img.shields.io/badge/portfolio-theocldt.dev-39d0d8?style=for-the-badge&labelColor=161b22"></a> <a href="https://www.linkedin.com/in/theo-cldt/"><img alt="LinkedIn" src="https://img.shields.io/badge/linkedin-theo--cldt-0a66c2?style=for-the-badge&logo=linkedin&logoColor=white&labelColor=161b22"></a> <a href="mailto:theoclaereboudt@gmail.com"><img alt="Email" src="https://img.shields.io/badge/email-theoclaereboudt%40gmail.com-a371f7?style=for-the-badge&logo=gmail&logoColor=white&labelColor=161b22"></a>

**🟢 Open to internships**: DevOps, platform or infrastructure roles

</div>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/terminal-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/terminal-light.svg">
  <img alt="neofetch-style summary: name, role, school, uptime, repos, contributions, streaks, languages, stack and status" src="assets/generated/terminal-dark.svg" width="100%">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/section-about-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/section-about-light.svg">
  <img alt="About" src="assets/generated/section-about-dark.svg" width="100%">
</picture>

I'm Théo, a **DevOps and infrastructure developer** who has finished the Common Core at **42 Mulhouse** 🇫🇷. I like owning everything between `git push` and production: the containers, the cluster, the deployments, the reverse proxy, the logs, and the services that run on top of them.

Before 42 I was already shipping to production: for over a year I built and ran, alone, a data platform for medical research. Today I containerize everything, run it on Kubernetes with GitOps, and design microservice architectures with Go and Python services. On the side, I make games in Godot.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/section-experience-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/section-experience-light.svg">
  <img alt="Experience" src="assets/generated/section-experience-dark.svg" width="100%">
</picture>

#### 🏥 Sole developer, thyroid research data platform · 2022 – 2023

An internal platform that gathers the public data on thyroid diseases from scientific publications and clinical trials, for a medical research team.

- **Collection:** daily automated ingestion from 2 platforms, by scraping (Requests, BeautifulSoup) and public APIs, scheduled with cron
- **Data:** a PostgreSQL database of several million records
- **App:** Django with accounts and roles for the team, and Dash dashboards embedded in Django
- **Production:** a VPS running Docker Compose behind an Nginx reverse proxy over HTTPS

`Python` `Django` `Dash` `PostgreSQL` `Docker Compose` `Nginx` `cron`

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/section-projects-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/section-projects-light.svg">
  <img alt="Projects" src="assets/generated/section-projects-dark.svg" width="100%">
</picture>

| | Project | What I did | Built with |
|:-:|---|---|---|
| 🛰️ | **BlueHub** <sub>(private, in progress)</sub> | A companion app for players of the game *Warpath*: player stats tracker, wiki, marketplace. I built the whole thing: a Go API and background worker that cache the game's API, one database per service, Keycloak auth with roles, and a Flutter client for desktop, mobile and web. | Go, PostgreSQL, Valkey, Keycloak, Caddy, Docker, Flutter |
| 🃏 | [**ft_transcendence**](https://github.com/Dlouu/ft_transcendence) | A real-time multiplayer UNO, built by a team of 4. **Technical lead:** I designed the microservices architecture and built the Flask API gateway, the auth flow (tokens, zero-trust between services), the MariaDB schema, Nginx with HTTPS and WebSockets, the ELK logging stack and S3 storage. | Python, Flask, NestJS, MariaDB, Nginx, ELK, AWS S3, Docker |
| ☸️ | [**Inception-of-things**](https://github.com/Inheert/Inception-of-things) | Kubernetes from the ground up: K3s clusters provisioned with Vagrant, then continuous deployment with K3d and Argo CD (GitOps). | Kubernetes, K3s, K3d, Argo CD, Vagrant |
| 🐚 | [**minishell**](https://github.com/Inheert/minishell) | A bash-like shell: lexer and parser, pipes, redirections, heredocs, environment variables, signals and builtins. | C |
| 🎮 | **Godot games** <sub>(private, in progress)</sub> | Games I build in my free time, in GDScript. | Godot, GDScript |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/section-stack-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/section-stack-light.svg">
  <img alt="Stack" src="assets/generated/section-stack-dark.svg" width="100%">
</picture>

```yaml
containers:  [Docker, Docker Compose, Dockerfiles]
orchestrate: [Kubernetes, K3s, K3d, Vagrant]
delivery:    [Argo CD (GitOps), GitHub Actions, cron]
network:     [Nginx, Caddy, HTTPS/TLS, reverse proxy, WebSockets]
observe:     [ELK (Elasticsearch, Logstash, Kibana)]
auth:        [Keycloak, OIDC, JWT, zero-trust between services]
backend:     [Go, Python, Django, Flask, PostgreSQL, MariaDB, Valkey]
```

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/section-languages-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/section-languages-light.svg">
  <img alt="Languages" src="assets/generated/section-languages-dark.svg" width="100%">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/languages-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/languages-light.svg">
  <img alt="Most used languages across public repositories" src="assets/generated/languages-dark.svg" width="100%">
</picture>

<details>
<summary><b>🇫🇷 Version française</b></summary>
<br>

Je suis Théo, **développeur DevOps et infrastructure**, Common Core validé à **42 Mulhouse**. Ce qui me plaît, c'est tout ce qui se passe entre le `git push` et la production : les conteneurs, le cluster, les déploiements, le reverse proxy, les logs, et les services qui tournent dessus.

- **Expérience :** de 2022 à 2023, seul développeur d'une plateforme interne pour une équipe de recherche médicale, qui rassemble les données publiques sur les pathologies de la thyroïde (publications scientifiques et essais cliniques). Collecte quotidienne automatisée (scraping et API publiques, cron), base PostgreSQL de plusieurs millions d'enregistrements, application Django avec comptes et rôles et tableaux de bord Dash, mise en production sur VPS avec Docker Compose derrière Nginx en HTTPS.
- **Projets :** BlueHub, une app compagnon pour le jeu *Warpath* (Go, PostgreSQL, Keycloak, Flutter) ; lead technique de ft_transcendence (architecture microservices, gateway, auth, ELK) ; Kubernetes avec K3s et Argo CD.
- **Je recherche un stage** en DevOps, plateforme ou infrastructure. Contact : [theoclaereboudt@gmail.com](mailto:theoclaereboudt@gmail.com) · [LinkedIn](https://www.linkedin.com/in/theo-cldt/) · [theocldt.dev](https://www.theocldt.dev/)

</details>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/section-how-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/section-how-light.svg">
  <img alt="How this page works" src="assets/generated/section-how-dark.svg" width="100%">
</picture>

No stats service, no visitor counter. The cards above are drawn by [`scripts/generate.py`](scripts/generate.py), standard-library Python only:

1. A [GitHub Action](.github/workflows/profile.yml) runs every night and asks the GraphQL API for my contributions, repos and languages.
2. The script draws each card twice, as hand-written SVG with CSS and SMIL animations, once for the dark theme and once for the light one. `<picture>` picks the one that matches yours.
3. The Action commits the result.


<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/footer-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/generated/footer-light.svg">
  <img alt="" src="assets/generated/footer-dark.svg" width="100%">
</picture>
