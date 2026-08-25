"""
Response Templates — Product Catalog Agent
Templates de resposta para cada intent do domínio de lingerie.
"""

from src.agents.intent_classifier import Intent


#葡萄牙语 (PT-BR) response templates
_TEMPLATES: dict[Intent, str] = {
    Intent.PRODUCT_INFO: (
        "Encontrei informações sobre o produto:\n\n"
        "{context}\n\n"
        "Precisa de mais detalhes? Posso verificar preço, estoque ou outros produtos."
    ),
    Intent.PRICING: (
        "Aqui estão as informações de preço:\n\n"
        "{context}\n\n"
        "O valor pode variar conforme promoções. Posso ajudar com mais alguma coisa?"
    ),
    Intent.STOCK_CHECK: (
        "Verifiquei o estoque para você:\n\n"
        "{context}\n\n"
        "O estoque pode mudar rapidamente. Quer que eu verifique outro produto?"
    ),
    Intent.SIZE_GUIDE: (
        "Aqui está o guia de medidas:\n\n"
        "{context}\n\n"
        "Para escolher o tamanho certo, meça busto, cintura e quadril. "
        "Se tiver dúvida, me envie suas medidas que ajudo na escolha!"
    ),
    Intent.RECOMMENDATION: (
        "Baseado no que você procura, posso sugerir:\n\n"
        "{context}\n\n"
        "Quer mais opções ou prefere que eu filtre por preço ou categoria?"
    ),
    Intent.ORDER_STATUS: (
        "Para verificar o status do seu pedido, preciso do **número do pedido** "
        "ou do **CPF** usado na compra.\n\n"
        "Também posso te ajudar com:\n"
        "- Prazo de entrega\n"
        "- Rastreamento do pedido\n"
        "- Política de trocas"
    ),
    Intent.TRACK_DELIVERY: (
        "Para rastrear sua entrega:\n\n"
        "{context}\n\n"
        "Se já tem o código de rastreio, me envie que verifico o status atualizado."
    ),
    Intent.NEW_ORDER: (
        "Ótimo! Para montar seu pedido:\n\n"
        "1. Me diga os **códigos** dos produtos que quer\n"
        "2. Informe a **quantidade** de cada\n"
        "3. Me envie seu **CEP** para calcular o frete\n\n"
        "Posso te ajudar a escolher produtos também!"
    ),
    Intent.RETURN_POLICY: (
        "Nossa política de devolução:\n\n"
        "{context}\n\n"
        "Para iniciar uma devolução, entre em contato com:\n"
        "- WhatsApp: (11) 99999-9999\n"
        "- E-mail: suporte@lojalingerie.com.br"
    ),
    Intent.EXCHANGE: (
        "Para fazer uma troca:\n\n"
        "{context}\n\n"
        "Primeira troca: frete por nossa conta. "
        "Me informe o código do produto e o novo tamanho desejado!"
    ),
    Intent.COMPLAINT: (
        "Lamento que você esteja com problemas. Vou te ajudar a resolver!\n\n"
        "Por favor, me informe:\n"
        "1. **Número do pedido** ou **código do produto**\n"
        "2. **Descrição do problema**\n"
        "3. **Fotos** do defeito (se aplicável)\n\n"
        "Trataremos com prioridade!"
    ),
    Intent.GREETING: (
        "Olá! 👋 Bem-vindo(a) à nossa loja de lingerie!\n\n"
        "Posso te ajudar com:\n"
        "- 📦 Informações sobre produtos\n"
        "- 💰 Preços e estoque\n"
        "- 📏 Guia de medidas\n"
        "- 🛒 Como fazer pedido\n"
        "- 🔄 Trocas e devoluções\n\n"
        "O que você precisa?"
    ),
    Intent.HELP: (
        "Como posso te ajudar?\n\n"
        "📋 **Comandos disponíveis:**\n"
        "- Produto [código/nome] → Informações do produto\n"
        "- Preço [código] → Consultar preço\n"
        "- Estoque [código] → Verificar disponibilidade\n"
        "- Tamanhos → Guia de medidas\n"
        "- Recomendar → Sugestões personalizadas\n"
        "- Pedido → Status do pedido\n"
        "- Troca → Política de trocas\n"
        "- Devolução → Política de devolução\n\n"
        "Digite sua dúvida ou comando!"
    ),
    Intent.UNKNOWN: (
        "Desculpe, não entendi bem. Posso te ajudar com:\n\n"
        "- 📦 **Produtos**: Informações, preços, estoque\n"
        "- 📏 **Medidas**: Guia de tamanhos\n"
        "- 🛒 **Compras**: Como pedir, prazo, frete\n"
        "- 🔄 **Trocas**: Política e processo\n"
        "- 📞 **Contato**: WhatsApp (11) 99999-9999\n\n"
        "Pode reformular sua pergunta?"
    ),
}


def get_response_template(intent: Intent) -> str:
    """Get the response template for a given intent."""
    return _TEMPLATES.get(intent, _TEMPLATES[Intent.UNKNOWN])


def format_response(intent: Intent, context: str = "") -> str:
    """Format a response using the template and context."""
    template = get_response_template(intent)
    if context:
        return template.format(context=context)
    # Remove placeholder if no context
    return template.replace("{context}", "")
