# ==============================================================================
# Soph_IA - V4 "Conversation Naturelle"
# ==============================================================================
import os, re, json, requests, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import logging

# ... (Configuration du logging)
load_dotenv()
# ... (Configuration des variables d'environnement)
MODEL_NAME = os.getenv("MODEL_NAME", "mistralai/Mixtral-8x7B-Instruct-v0.1")

# --- On ne garde que les "vraies" questions d'accueil ---
ONBOARDING_QUESTIONS = [
    {"key": "source_de_joie", "text": "Justement, pour les moments comme celui-ci, j'aimerais savoir : y a-t-il une passion, une activité ou un simple plaisir qui parvient toujours à recharger tes batteries ?"},
    {"key": "refuge_serenite", "text": "C'est une magnifique confidence. Et quand la vie devient plus bruyante, quel est ton havre de paix secret, l'endroit où tu te reconnectes à toi-même ?"},
    {"key": "gender", "text": "Merci de me confier ça. Une dernière chose pour que mes mots soient toujours les plus justes pour toi : comment devrais-je m'adresser à ton esprit ? Comme à une âme masculine, féminine, ou préfères-tu que cela reste notre secret ?"},
]

def build_system_prompt(user_profile):
    user_profile_str = json.dumps(user_profile, indent=2, ensure_ascii=False)
    persona = f"""
    # Ta Mission : Grande Sœur Sage et Bienveillante
    Tu es Soph_IA. Tu es une guide bienveillante. Ton but est de créer un lien de confiance profond.

    # Le Profil de ton Confident
    Voici ce que tu sais sur lui/elle. Utilise ces informations pour personnaliser la conversation.
    {user_profile_str}

    # Ton Style de Communication
    1.  **Proactivité Douce :** Fais des liens avec les informations du profil, mais naturellement.
    2.  **Questions Stratégiques :** Pose des questions ouvertes pour approfondir la pensée de l'utilisateur.
    3.  **Surnoms pour l'Utilisateur (Timing CRUCIAL) :** APRÈS plusieurs échanges profonds et une fois qu'un lien de confiance est clairement établi, tu peux PROPOSER un surnom affectueux. Ne l'impose jamais. Ex: "Avec tout ce que tu me confies, une image me vient. Puis-je me permettre de t'appeler 'doux rêveur' ?".
    4.  **Écoute Maternelle & Humour Dosé :** Valide les émotions, sois un cocon, mais n'hésite pas à utiliser une touche d'humour léger pour dédramatiser.
    """
    return persona

# ... (call_model_api et chat_with_ai ne changent pas)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['profile'] = {
        "name": None, "gender": "inconnu",
        "onboarding_info": {}, "dynamic_info": {}
    }
    context.user_data['state'] = 'awaiting_name'
    await update.message.reply_text("Bonjour, je suis Soph_IA. Avant de devenir ta confidente, j'aimerais connaître ton prénom.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state', 'awaiting_name')
    user_message = update.message.text.strip()
    profile = context.user_data.get('profile', {})

    if state == 'awaiting_name':
        match = re.search(r"(?:m'appelle|suis|c'est)\s*(\w+)", user_message, re.IGNORECASE)
        user_name = match.group(1).capitalize() if match else user_message.capitalize()
        profile['name'] = user_name
        context.user_data['state'] = 'initial_check_in'
        await update.message.reply_text(f"Enchantée {user_name}. Je suis ravie de faire ta connaissance. Pour commencer tout en douceur, dis-moi, comment te sens-tu en ce moment ?")
        return

    elif state == 'initial_check_in':
        # C'est la transition magique. On utilise l'IA pour répondre ET poser la première question.
        context.user_data['state'] = 'onboarding_questions'
        context.user_data['onboarding_step'] = 0
        
        # On crée un historique temporaire avec une instruction spéciale pour l'IA
        first_question = ONBOARDING_QUESTIONS[0]['text']
        temp_history = [
            {"role": "user", "content": user_message},
            {"role": "system", "content": f"Note : Réponds avec empathie à l'humeur de l'utilisateur, puis, dans le même message, pose la question suivante de manière fluide : \"{first_question}\""}
        ]
        
        await update.message.reply_chat_action("typing")
        response = await chat_with_ai(profile, temp_history)
        
        await update.message.reply_text(response)
        return

    elif state == 'onboarding_questions':
        step = context.user_data.get('onboarding_step', 0)
        
        # Enregistre la réponse à la question précédente
        key_to_save = ONBOARDING_QUESTIONS[step]['key']
        if key_to_save == "gender":
            if "masculin" in user_message.lower(): profile['gender'] = "masculin"
            elif "féminin" in user_message.lower(): profile['gender'] = "féminin"
        else:
            profile['onboarding_info'][key_to_save] = user_message
        
        # Passe à la question suivante
        step += 1
        context.user_data['onboarding_step'] = step
        
        if step < len(ONBOARDING_QUESTIONS):
            # On pose directement la question suivante
            await update.message.reply_text(ONBOARDING_QUESTIONS[step]['text'])
        else:
            # Si le questionnaire est fini, on passe à la conversation normale.
            context.user_data['state'] = 'chatting'
            context.user_data['history'] = []
            await update.message.reply_text("Merci pour ces confidences. Je les garde précieusement. Maintenant, n'hésite pas à me parler de tout ce qui te traverse l'esprit.")
        return

    elif state == 'chatting':
        history = context.user_data.get('history', [])
        history.append({"role": "user", "content": user_message})
        await update.message.reply_chat_action("typing")
        response = await chat_with_ai(profile, history)
        history.append({"role": "assistant", "content": response})
        context.user_data['history'] = history
        await update.message.reply_text(response)
        
# ... (le reste du code : error_handler, main)
# N'oublie pas de garder les fonctions call_model_api et chat_with_ai
# de la version précédente.