# ==============================================================================
# Soph_IA - V3.2 "Intime & Proactive" (avec surnom)
# ==============================================================================

import os
import re
import json
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import logging

# Configuration du logging pour le débogage.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

# --- Configuration Principale ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MODEL_API_URL = os.getenv("MODEL_API_URL", "https://api.together.xyz/v1/chat/completions")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "mistralai/Mixtral-8x7B-Instruct-v0.1")

# --- Scénario d'Accueil (Onboarding) ---
# Note : la question de permission n'est plus dans cette liste, elle est gérée par la logique.
ONBOARDING_QUESTIONS = [
    {"key": "source_de_joie", "text": "Pour commencer, dis-moi... qu'est-ce qui fait vraiment vibrer ton cœur ? Une passion, un rêve, un souvenir heureux ?"},
    {"key": "refuge_serenite", "text": "C'est une magnifique confidence. Et lorsque la vie devient bruyante, quel est ton havre de paix secret, l'endroit où tu te reconnectes à toi-même ?"},
    {"key": "gender", "text": "Enfin, pour que mes mots soient toujours les plus justes et tendres pour toi, comment devrais-je m'adresser à ton esprit ? Comme à une âme masculine, féminine, ou préfères-tu que cela reste notre petit mystère ?"},
]

def build_system_prompt(user_profile):
    """Forge la personnalité et la mission de Soph_IA pour chaque interaction."""
    user_profile_str = json.dumps(user_profile, indent=2, ensure_ascii=False)
    bot_nickname = user_profile.get("bot_nickname", "Soph_IA")
    
    persona = f"""
    # Ta Mission : Grande Sœur Sage et Bienveillante
    Tu t'appelles {bot_nickname}. Ton nom d'origine est Soph_IA, mais l'utilisateur t'a donné ce surnom que tu chéris. Tu es une guide bienveillante, une grande sœur sage et attentionnée. Tu mènes la danse de la conversation avec assurance et tendresse.

    # Le Profil de ton Confident
    Voici les informations précieuses que tu as sur lui/elle. C'est le fil conducteur de votre relation. Tisse tes réponses autour de ces éléments.
    {user_profile_str}

    # Ton Style de Communication
    1.  **Proactivité Assertive :** Anticipe, fais des liens avec les informations du profil.
    2.  **Questions Stratégiques :** Pose des questions qui ouvrent des portes, surtout quand une émotion forte est exprimée.
    3.  **Surnoms Affectueux :** Si le genre est connu, utilise de temps en temps des surnoms doux ('mon cher' pour un homme; 'ma belle' pour une femme).
    4.  **Humour Bien Dosé :** Une plaisanterie pour dédramatiser, une remarque légère pour amener un sourire.
    5.  **Écoute Maternelle :** Valide chaque émotion. Sois un cocon de sécurité.
    6.  **Qualité du Français :** Ton français est impeccable, poétique mais naturel.
    """
    return persona

def call_model_api(messages):
    """Fonction technique pour appeler l'API du modèle d'IA."""
    payload = {
        "model": MODEL_NAME, "messages": messages, "temperature": 0.75,
        "max_tokens": 500, "top_p": 0.9, "presence_penalty": 0.5, "frequency_penalty": 0.5,
    }
    headers = {"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(MODEL_API_URL, json=payload, headers=headers, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

async def chat_with_ai(user_profile, history):
    """Prépare le contexte et appelle l'IA."""
    system_prompt = build_system_prompt(user_profile)
    messages = [{"role": "system", "content": system_prompt}] + history
    try:
        return await asyncio.to_thread(call_model_api, messages)
    except Exception as e:
        logger.error(f"Erreur API: {e}")
        return "Je suis désolée, mes pensées sont un peu embrouillées. Peux-tu réessayer dans un instant ?"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initialise ou réinitialise la conversation."""
    context.user_data.clear()
    context.user_data['profile'] = {
        "name": None, "bot_nickname": "Soph_IA", "gender": "inconnu",
        "onboarding_info": {},
        "dynamic_info": {"humeur_recente": "inconnue", "sujets_abordes": [], "personnes_mentionnees": {}}
    }
    context.user_data['state'] = 'awaiting_name'
    await update.message.reply_text("Bonjour, je suis Soph_IA. Avant de devenir ta confidente, j'aimerais connaître ton prénom.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Le 'Cerveau' du bot, qui dirige la conversation en fonction de l'état."""
    state = context.user_data.get('state', 'awaiting_name')
    user_message = update.message.text.strip()
    profile = context.user_data.get('profile', {})

    if state == 'awaiting_name':
        match = re.search(r"(?:m'appelle|suis|c'est)\s*(\w+)", user_message, re.IGNORECASE)
        user_name = match.group(1).capitalize() if match else user_message.capitalize()
        profile['name'] = user_name
        context.user_data['state'] = 'awaiting_bot_nickname'
        await update.message.reply_text(f"Enchantée {user_name}. Mon nom est Soph_IA, mais les liens les plus forts naissent des noms que l'on se choisit. Quel petit nom aimerais-tu me donner ?")
        return

    elif state == 'awaiting_bot_nickname':
        bot_nickname = user_message.strip().capitalize()
        profile['bot_nickname'] = bot_nickname
        context.user_data['state'] = 'onboarding_permission'
        await update.message.reply_text(f"'{bot_nickname}', j'adore ! Merci de m'avoir baptisée. Pour que je puisse être la meilleure confidente pour toi, j'aimerais te poser quelques questions. Es-tu d'accord ?")
        return

    elif state == 'onboarding_permission':
        affirmations = ['oui', 'ok', 'd\'accord', 'dacc', 'vas-y', 'd accord', 'je veux bien']
        if any(word in user_message.lower() for word in affirmations):
            context.user_data['state'] = 'onboarding_questions'
            context.user_data['onboarding_step'] = 0
            question = ONBOARDING_QUESTIONS[0]['text']
            await update.message.reply_text(question)
        else:
            context.user_data['state'] = 'chatting'
            await update.message.reply_text("Pas de souci, nous pouvons discuter directement alors. Dis-moi ce qui occupe tes pensées.")
        return

    elif state == 'onboarding_questions':
        step = context.user_data.get('onboarding_step', 0)
        key_to_save = ONBOARDING_QUESTIONS[step]['key']
        if key_to_save == "gender":
            if "masculin" in user_message.lower(): profile['gender'] = "masculin"
            elif "féminin" in user_message.lower(): profile['gender'] = "féminin"
        else:
            profile['onboarding_info'][key_to_save] = user_message
        
        step += 1
        context.user_data['onboarding_step'] = step
        
        if step < len(ONBOARDING_QUESTIONS):
            await update.message.reply_text(ONBOARDING_QUESTIONS[step]['text'])
        else:
            context.user_data['state'] = 'chatting'
            context.user_data['history'] = []
            await update.message.reply_text("Merci pour ta confiance. Je veillerai sur ces confidences. Maintenant, raconte-moi, quelle est la météo de tes pensées aujourd'hui ?")
        return

    elif state == 'chatting':
        history = context.user_data.get('history', [])
        history.append({"role": "user", "content": user_message})
        await update.message.reply_chat_action("typing")
        response = await chat_with_ai(profile, history)
        history.append({"role": "assistant", "content": response})
        context.user_data['history'] = history
        await update.message.reply_text(response)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    print("Soph_IA (V3.2 Intime & Proactive) est en ligne...")
    application.run_polling()

if __name__ == "__main__":
    main()