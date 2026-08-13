---
name: Multiagente de pedidos de comida para VerdeFit
description: Servicio de pedidos de comida automatizada para algunos distritos de Lima.
---

## Problema

Los clientes de VerdeFit necesitan realizar reservas de pedidos para envío a sus lugares de trabajo o para recogerlos en el local. Actualmente, VerdeFit gestiona los pedidos de forma manual, esto ha generado problemas:

- Sobrecarga operativa
- Crecimiento limitado

## Solución

Debido al crecimiento, se sugiere utilizar el ecosistema de Google ADK de múltiples agentes especializados que trabajan en coordinación para automatizar el proceso de pedidos.

## 🛠 Tech Stack

- Python 3.13
- Neon utilizando PostgreSQL para base de datos
- Google ADK para trabajar con multiples agentes

## Configuración

> [!IMPORTANT]
> Actualiza correctamente las credenciales del `.env.template` y debes desactivar el protocolo de versión 6 TCP/IPv6 para evitar demoras con la conexión en Neon.
