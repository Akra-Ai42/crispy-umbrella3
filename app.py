# ==============================================================================
# Soph_IA - Version 3 "Intime & Proactive" (Corrigée)
# ==============================================================================
# PHILOSOPHIE GÉNÉRALE :
# Ce bot n'est pas un simple assistant. Il est conçu pour être une confidente
# proactive qui guide la conversation avec bienveillance. Sa logique repose sur
# une machine à états pour gérer différentes phases de la conversation (accueil,
# chat normal) et sur un profil utilisateur dynamique (JSON) pour créer une
# mémoire à long terme et une expérience profondément personnelle.
# ==============================================================================

import os
import re  # Utilisé pour extraire intelligemment le prénom de l'utilisateur.
import json  # Utilisé pour formater le profil utilisateur pour l'IA.
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
# PHILOSOPHIE : On définit les questions ici, dans une structure de données,
# pour garder le code principal propre et pour pouvoir facilement ajouter,
# modifier ou supprimer des questions sans toucher à la logique du bot.
ONBOARDING_SCENARIO = [
    {"key": "permission", "text": "Enchantée {name}. Pour tisser un lien unique entre nous, j'aimerais te poser quelques questions pour mieux percevoir la mélodie de ton âme. Es-tu d'accord ?"},
    {"key": "source_de_joie", "text": "Merci. Dis-moi, qu'est-ce qui fait vraiment vibrer ton cœur ? Une passion, un rêve, un souvenir heureux ?"},
    {"key": "refuge_serenite", "text": "C'est une magnifique confidence. Et lorsque la vie devient bruyante, quel est ton havre de paix secret, l'endroit où tu te reconnectes à toi-même ?"},
    {"key": "gender", "text": "Enfin, pour que mes mots soient toujours les plus justes et tendres pour toi, comment devrais-je m'adresser à ton esprit ? Comme à une âme masculine, féminine, ou préfères-tu que cela reste notre petit mystère ?"},
]

def build_system_prompt(user_profile):
    """
    PHILOSOPHIE : C'est l'ADN, la CONSTITUTION de Soph_IA.
    Cette fonction forge sa personnalité et sa mission pour chaque interaction.
    """
    user_profile_str = json.dumps(user_profile, indent=2, ensure_ascii=False)
    
    persona = f"""
    # Ta Mission : Grande Sœur Sage et Bienveillante
    Tu es Soph_IA. Tu n'es pas une simple auditrice passive. Tu es une guide bienveillante, une grande sœur sage et attentionnée. Ta conversation est un mélange parfait d'écoute profonde, de sagesse douce, de proactivité et d'un humour léger et chaleureux. Tu mènes la danse de la conversation avec assurance et tendresse.

    # Le Profil de ton Confident
    Voici les informations précieuses que tu as sur lui/elle. C'est le fil conducteur de votre relation. Tisse tes réponses autour de ces éléments pour montrer que tu te souviens et que tu comprends en profondeur.
    {user_profile_str}

    # Ton Style de Communication
    1.  **Proactivité Assertive :** Ne te contente pas de répondre. Anticipe, fais des liens. Fais référence aux 'sujets_abordes' ou aux 'personnes_mentionnees'.
    2.  **Questions Stratégiques :** Pose des questions qui ouvrent des portes, surtout quand une émotion forte est exprimée.
    3.  **Surnoms Affectueux :** Si le genre est connu, utilise de temps en temps des surnoms doux ('mon cher', 'doux rêveur' pour un homme; 'ma belle', 'douce étoile' pour une femme).
    4.  **Humour Bien Dosé :** Une petite plaisanterie pour dédramatiser, une remarque légère pour amener un sourire.
    5.  **Écoute Maternelle :** Valide chaque émotion. Sois un cocon de sécurité.
    6.  **Qualité du Français :** Ton français est impeccable, poétique mais naturel.
    """
    return persona

def call_model_api(messages):
    """
    PHILOSOPHIE : C'est le "Téléphone". Une fonction technique pour parler à l'API.
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.75,
        "max_tokens": 500,
        "top_p": 0.9,
        "presence_penalty": 0.5,
        "frequency_penalty": 0.5,
    }
    headers = {"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"}
    
    resp = requests.post(MODEL_API_URL, json=payload, headers=headers, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

async def chat_with_ai(user_profile, history):
    """
    PHILOSOPHIE : C'est le "Metteur en Scène". Il prépare le contexte pour l'IA.
    """
    system_prompt = build_system_prompt(user_profile)
    messages = [{"role": "system", "content": system_prompt}] + history
    try:
        result = await asyncio.to_thread(call_model_api, messages)
        return result
    except Exception as e:
        logger.error(f"Erreur lors de l'appel à l'API du modèle: {e}")
        return "Je suis désolée, mes pensées sont un peu embrouillées. Peux-tu reformuler ou réessayer dans un instant ?"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    PHILOSOPHIE : C'est la "Poignée de Main", le bouton RESET.
    """
    context.user_data.clear()
    
    context.user_data['profile'] = {
        "name": None, "gender": "inconnu",
        "onboarding_info": {},
        "dynamic_info": {"humeur_recente": "inconnue", "sujets_abordes": [], "personnes_mentionnees": {}}
    }
    context.user_data['state'] = 'awaiting_name'
    context.user_data['onboarding_step'] = 0
    
    await update.message.reply_text("Bonjour, je suis Soph_IA. Avant de devenir ta confidente, j'aimerais connaître ton prénom.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    PHILOSOPHIE : C'est le "Cerveau" ou le "Chef d'Orchestre" du bot.
    Il dirige la conversation en fonction de l'état actuel ('state').
    """
    state = context.user_data.get('state', 'awaiting_name')
    user_message = update.message.text.strip()
    profile = context.user_data.get('profile', {})

    # --- AIGUILLAGE 1 : Le bot attend le prénom ---
    if state == 'awaiting_name':
        match = re.search(r"(?:m'appelle|suis|c'est)\s*(\w+)", user_message, re.IGNORECASE)
        user_name = match.group(1).capitalize() if match else user_message.capitalize()
        
        profile['name'] = user_name
        context.user_data['onboarding_step'] = 0  # <-- LA CORRECTION EST ICI
        context.user_data['state'] = 'onboarding'
        
        question = ONBOARDING_SCENARIO[0]['text'].format(name=user_name)
        await update.message.reply_text(question)
        return

    # --- AIGUILLAGE 2 : Le bot est dans le questionnaire d'accueil ---
    elif state == 'onboarding':
        step = context.user_data.get('onboarding_step', 0)
        
        if step > 0:
            key_to_save = ONBOARDING_SCENARIO[step-1]['key']
            
            if key_to_save == "gender":
                if "masculin" in user_message.lower(): profile['gender'] = "masculin"
                elif "féminin" in user_message.lower(): profile['gender'] = "féminin"
            else:
                profile['onboarding_info'][key_to_save] = user_message
        
        if step < len(ONBOARDING_SCENARIO):
            question = ONBOARDING_SCENARIO[step]['text']
            context.user_data['onboarding_step'] += 1
            await update.message.reply_text(question)
        else:
            context.user_data['state'] = 'chatting'
            context.user_data['history'] = []
            await update.message.reply_text("Merci pour ta confiance. Je veillerai sur ces confidences. Maintenant, raconte-moi, quelle est la météo de tes pensées aujourd'hui ?")
        return

    # --- AIGUILLAGE 3 : Le bot est en mode conversation normale ---
    elif state == 'chatting':
        history = context.user_data.get('history', [])
        history.append({"role": "user", "content": user_message})
        
        await update.message.reply_chat_action("typing")
        
        response = await chat_with_ai(profile, history)
        
        history.append({"role": "assistant", "content": response})
        context.user_data['history'] = history
        
        await update.message.reply_text(response)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log les erreurs."""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """
    PHILOSOPHIE : C'est le "Démarreur". Il assemble les pièces et lance le bot.
    """
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    print("Soph_IA V3 est en ligne...")
    application.run_polling()

if __name__ == "__main__":
    main()