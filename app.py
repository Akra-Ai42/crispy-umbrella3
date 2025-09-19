# ==============================================================================
# Soph_IA - Version 3 "Intime & Proactive"
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

# ==============================================================================
# SECTION 1 : Le Cœur de l'IA - Communication avec le Modèle
# ==============================================================================

def build_system_prompt(user_profile):
    """
    PHILOSOPHIE : C'est l'ADN, la CONSTITUTION de Soph_IA.
    Cette fonction forge sa personnalité et sa mission pour chaque interaction.
    Elle prend le profil de l'utilisateur et l'injecte dans le "cerveau" de l'IA.
    C'est ici que l'on sculpte son âme.
    """
    # On transforme le dictionnaire du profil en une chaîne de texte formatée (JSON)
    # que le modèle d'IA peut facilement lire et comprendre.
    user_profile_str = json.dumps(user_profile, indent=2, ensure_ascii=False)
    
    # Le prompt système est le texte le plus important. C'est le briefing de mission de l'IA.
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
    PHILOSOPHIE : C'est le "Téléphone". Une fonction purement technique qui ne fait
    qu'une chose : prendre un message, le formater correctement, l'envoyer à l'API
    externe et retourner la réponse. Elle gère la communication brute.
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.75,  # Contrôle la créativité.
        "max_tokens": 500,
        "top_p": 0.9,
        # Paramètres anti-répétition ajoutés en V3.
        "presence_penalty": 0.5, # Empêche de revenir sur les mêmes sujets en boucle.
        "frequency_penalty": 0.5, # Empêche de répéter les mêmes mots.
    }
    headers = {"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"}
    
    # On envoie la requête et on gère les erreurs éventuelles.
    resp = requests.post(MODEL_API_URL, json=payload, headers=headers, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

async def chat_with_ai(user_profile, history):
    """
    PHILOSOPHIE : C'est le "Metteur en Scène". Il prépare tout le contexte
    nécessaire avant de "lancer la scène" (appeler l'IA). C'est le pont entre la
    logique structurée de notre bot et l'intelligence créative du modèle d'IA.
    """
    # 1. On forge la personnalité et le contexte grâce au prompt système.
    system_prompt = build_system_prompt(user_profile)
    
    # 2. On assemble le dossier complet : Mission (prompt) + Contexte (historique).
    messages = [{"role": "system", "content": system_prompt}] + history
    
    # 3. On délègue l'acte de "penser" à la fonction qui appelle l'API.
    try:
        result = await asyncio.to_thread(call_model_api, messages)
        return result
    except Exception as e:
        logger.error(f"Erreur lors de l'appel à l'API du modèle: {e}")
        return "Je suis désolée, mes pensées sont un peu embrouillées. Peux-tu reformuler ou réessayer dans un instant ?"

# ==============================================================================
# SECTION 2 : La Logique du Bot - Gestion des Interactions Telegram
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    PHILOSOPHIE : C'est la "Poignée de Main", le bouton RESET.
    Il garantit que chaque nouvelle conversation démarre sur des bases saines,
    propres et dans un état initial connu.
    """
    # On efface toutes les données de la conversation précédente pour la confidentialité.
    context.user_data.clear()
    
    # On crée la structure vide du profil pour ce nouvel utilisateur.
    context.user_data['profile'] = {
        "name": None, "gender": "inconnu",
        "onboarding_info": {},
        "dynamic_info": {"humeur_recente": "inconnue", "sujets_abordes": [], "personnes_mentionnees": {}}
    }
    # On définit l'état initial : le bot attend le prénom de l'utilisateur.
    context.user_data['state'] = 'awaiting_name'
    context.user_data['onboarding_step'] = 0 # Le compteur pour le questionnaire.
    
    # On envoie le premier message.
    await update.message.reply_text("Bonjour, je suis Soph_IA. Avant de devenir ta confidente, j'aimerais connaître ton prénom.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    PHILOSOPHIE : C'est le "Cerveau" ou le "Chef d'Orchestre" du bot.
    Cette fonction est le cœur de la logique. Elle ne pense pas, mais elle dirige
    la conversation en agissant comme un aiguilleur en fonction de l'état
    actuel de la discussion ('state').
    """
    # On récupère l'état actuel et le message de l'utilisateur.
    state = context.user_data.get('state', 'awaiting_name')
    user_message = update.message.text.strip()
    profile = context.user_data.get('profile', {})

    # --- AIGUILLAGE 1 : Le bot attend le prénom ---
    if state == 'awaiting_name':
        # On utilise une expression régulière pour extraire le prénom de la phrase.
        match = re.search(r"(?:m'appelle|suis|c'est)\s*(\w+)", user_message, re.IGNORECASE)
        user_name = match.group(1).capitalize() if match else user_message.capitalize()
        
        # On met à jour le profil et on passe à l'état suivant.
        profile['name'] = user_name
        context.user_data['state'] = 'onboarding'
        
        # On pose la première question du scénario d'accueil.
        question = ONBOARDING_SCENARIO[0]['text'].format(name=user_name)
        await update.message.reply_text(question)
        return

    # --- AIGUILLAGE 2 : Le bot est dans le questionnaire d'accueil ---
    elif state == 'onboarding':
        step = context.user_data.get('onboarding_step', 0)
        
        # On enregistre la réponse à la question qui vient d'être posée.
        if step > 0: # On ignore la réponse à la question de permission (la première).
            key_to_save = ONBOARDING_SCENARIO[step-1]['key']
            
            # Cas spécial pour la question sur le genre.
            if key_to_save == "gender":
                if "masculin" in user_message.lower(): profile['gender'] = "masculin"
                elif "féminin" in user_message.lower(): profile['gender'] = "féminin"
            else:
                profile['onboarding_info'][key_to_save] = user_message
        
        # On regarde s'il y a une question suivante à poser.
        if step < len(ONBOARDING_SCENARIO):
            question = ONBOARDING_SCENARIO[step]['text']
            context.user_data['onboarding_step'] += 1 # On incrémente le compteur.
            await update.message.reply_text(question)
        else:
            # Si le questionnaire est fini, on passe à l'état de conversation normale.
            context.user_data['state'] = 'chatting'
            context.user_data['history'] = []
            await update.message.reply_text("Merci pour ta confiance. Je veillerai sur ces confidences. Maintenant, raconte-moi, quelle est la météo de tes pensées aujourd'hui ?")
        return

    # --- AIGUILLAGE 3 : Le bot est en mode conversation normale ---
    elif state == 'chatting':
        history = context.user_data.get('history', [])
        history.append({"role": "user", "content": user_message})
        
        await update.message.reply_chat_action("typing") # Affiche "Soph_IA est en train d'écrire...".
        
        # On appelle le "Metteur en Scène" pour qu'il prépare et obtienne la réponse de l'IA.
        response = await chat_with_ai(profile, history)
        
        # On sauvegarde la réponse pour garder le contexte.
        history.append({"role": "assistant", "content": response})
        context.user_data['history'] = history
        
        # On envoie la réponse à l'utilisateur.
        await update.message.reply_text(response)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log les erreurs pour pouvoir les analyser."""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """
    PHILOSOPHIE : C'est le "Démarreur". Cette fonction assemble toutes les pièces
    du puzzle, branche les câbles et appuie sur le bouton "On".
    """
    # On crée l'application avec le token du bot.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # On branche nos fonctions aux bons événements.
    application.add_handler(CommandHandler("start", start)) # Si l'utilisateur tape /start -> appeler start()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)) # Si message texte normal -> appeler handle_message()
    application.add_error_handler(error_handler) # En cas d'erreur -> appeler error_handler()

    # On lance le bot.
    print("Soph_IA V3 est en ligne...")
    application.run_polling()

if __name__ == "__main__":
    main()