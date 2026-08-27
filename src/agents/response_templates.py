"""
Response Templates — Maria (Assistente Virtual)
Templates de resposta para cada intent.

Cada intent possui uma ou mais variantes de resposta. Quando há mais de
uma variante, uma é escolhida aleatoriamente a cada chamada para evitar
que a conversa soe repetitiva/robotizada em interações consecutivas.
"""

import random

from src.agents.intent_classifier import Intent


_TEMPLATES: dict[Intent, list[str]] = {
    Intent.PRODUCT_INFO: [
        "Encontrei isso sobre o produto:\n\n{context}\n\nQuer saber o preço ou o estoque?",
        "Olha só o que encontrei:\n\n{context}\n\nQuer que eu confira mais alguma coisa?",
    ],
    Intent.PRICING: [
        "O preço é **{context}**. Quer ver outro produto?",
        "Esse produto sai por **{context}**. Posso comparar com outra opção.",
    ],
    Intent.STOCK_CHECK: [
        "Consultei o estoque:\n\n{context}\n\nQuer que eu veja outro item?",
        "O estoque está assim:\n\n{context}\n\nPrecisa consultar outro produto?",
    ],
    Intent.SIZE_GUIDE: [
        "Sobre medidas:\n\n{context}\n\nSe me mandar suas medidas, ajudo a escolher o tamanho.",
    ],
    Intent.USER_MEASUREMENT: [
        "Anotei suas medidas! Vou te ajudar a escolher o tamanho certo.",
    ],
    Intent.RECOMMENDATION: [
        "Separei uma opção pra você:\n\n{context}\n\nQuer mais sugestões?",
        "Acho que essa opção pode combinar com o que você procura:\n\n{context}\n\nQuer ver outras?",
    ],
    Intent.ORDER_STATUS: [
        "Pra eu localizar seu pedido, me passa o **número do pedido** ou o **CPF** usado na compra.",
        "Consigo verificar isso! Me manda o número do pedido (ou o CPF da compra) que eu já confiro pra você.",
    ],
    Intent.TRACK_DELIVERY: [
        "Sobre a entrega:\n\n{context}\n\nSe já tiver o código de rastreio, me manda que eu confirmo o status atualizado.",
    ],
    Intent.NEW_ORDER: [
        "Bora fechar seu pedido! Preciso de três coisas:\n\n1. Os **códigos** dos produtos\n2. A **quantidade** de cada um\n3. Seu **CEP**, pra calcular o frete\n\nSe quiser, te ajudo a escolher os produtos também.",
    ],
    Intent.RETURN_POLICY: [
        "Sobre devolução:\n\n{context}\n\nQuer que eu explique como iniciar?",
    ],
    Intent.EXCHANGE: [
        "Sobre troca:\n\n{context}\n\nMe diga o código e o tamanho desejado.",
    ],
    Intent.COMPLAINT: [
        "Poxa, sinto muito por isso — vamos resolver. Me manda:\n\n1. Número do pedido ou código do produto\n2. O que aconteceu\n3. Se possível, uma foto do problema\n\nAssim que eu tiver isso, priorizo seu caso.",
    ],
    Intent.GREETING: [
        "Oi! Eu sou a Maria 👋 Posso te ajudar com produtos, preços, medidas, pedidos ou trocas. O que você precisa hoje?",
        "Olá! Aqui é a Maria, tudo bem? Me conta o que você está procurando que eu te ajudo a encontrar.",
        "Tudo bem sim! 😊 Sou a Maria, sua assistente. Em que posso te ajudar hoje?",
        "Oi! Tudo ótimo por aqui! Sou a Maria e estou pronta pra te ajudar. Procura alguma peça específica?",
        "Fala! Tudo joia! 😄 Me conta, quer ver calcinhas, sutiãs ou alguma outra coisa?",
    ],
    Intent.HELP: [
        (
            "Claro, posso te ajudar com:\n\n"
            "- Informações e preço de produto\n"
            "- Disponibilidade em estoque\n"
            "- Guia de medidas\n"
            "- Status de pedido e rastreio\n"
            "- Trocas e devoluções\n\n"
            "É só me contar o que precisa, do seu jeito, que eu entendo."
        ),
    ],
    Intent.UNKNOWN: [
        "Hmm, não peguei bem essa. Você quer saber sobre produto, preço, medidas, pedido ou troca?",
        "Não entendi direito, desculpa! Pode me explicar de outro jeito? Se ajudar, posso falar sobre produtos, preços, tamanhos ou pedidos.",
    ],
    # PDV Actions
    Intent.LOOKUP_CUSTOMER: [
        "Buscando o cliente...\n\n{context}",
    ],
    Intent.CREATE_SALE: [
        "{context}",
    ],
    Intent.GET_DAILY_REPORT: [
        "{context}",
    ],
    Intent.GET_CUSTOMER_HISTORY: [
        "{context}",
    ],
    Intent.GET_CUSTOMER_CREDIT: [
        "{context}",
    ],
}


def get_response_template(intent: Intent) -> str:
    """Retorna uma variante de template para o intent informado.

    Quando há mais de uma variante cadastrada, uma delas é escolhida
    aleatoriamente para reduzir a sensação de resposta "engessada".
    """
    variants = _TEMPLATES.get(intent, _TEMPLATES[Intent.UNKNOWN])
    return random.choice(variants)


def format_response(intent: Intent, context: str = "") -> str:
    """Formata a resposta final a partir do template e do contexto.

    Se o template esperar `{context}` e nenhum contexto for informado,
    remove o placeholder evitando lacunas estranhas na frase.
    """
    if context:
        # Keep RAG replies readable in chat: one relevant chunk and a short limit.
        context = context.split("\n---\n", 1)[0].strip()
        if len(context) > 700:
            context = context[:697].rsplit(" ", 1)[0] + "..."

    template = get_response_template(intent)
    if context:
        return template.format(context=context)
    return template.replace("{context}", "").strip()