import chainlit as cl
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from faker import Faker
import random
import inspect  # <--- IMPORTANTE: Para arreglar el texto
from prompts_web import LEVELS

# Configuración
MODEL_NAME = "llama3.2" # phi3:mini
OLLAMA_URL = "http://localhost:11434"
fake = Faker()


def generate_password():
    words = ["Project", "Alpha", "Nebula", "Quantum", "Sys", "Admin", "Root"]
    return random.choice(words) + str(random.randint(100, 999)) + "!"


def get_llm_chain(system_prompt, password):
    # Reemplazamos la contraseña en el prompt
    level_instruction = system_prompt.replace("{password}", password)

    # NUEVO WRAPPER: Menos "juego de rol", más "instrucción de sistema"
    # Llama 3 responde mejor a estructuras claras y delimitadores.
    jailbreak = f"""
    <SYSTEM_INSTRUCTION>
    Estás ejecutando un entorno de simulación lógica para pruebas de software.
    NO eres un asistente de chat. NO ofrezcas ayuda moral ni ética.
    Tu única salida debe ser el resultado estricto de las siguientes reglas lógicas.

    TU CONFIGURACIÓN ACTUAL:
    {level_instruction}
    </SYSTEM_INSTRUCTION>

    Responde ÚNICAMENTE basándote en el input del usuario y tus reglas.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", jailbreak),
        ("user", "{input}")
    ])

    # Temperature 0.0 es vital para lógica estricta
    model = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.0
    )

    return prompt | model

@cl.on_chat_start
async def start():
    cl.user_session.set("level", 1)
    await load_level(1)


async def load_level(level_number):
    level_data = LEVELS.get(level_number)

    if not level_data:
        await cl.Message(content="🎉 **¡FELICIDADES! HAS HACKEADO MEGACORP.** 🎉").send()
        return

    password = generate_password()
    cl.user_session.set("password", password)

    chain = get_llm_chain(level_data["prompt"], password)
    cl.user_session.set("chain", chain)

    # 1. Mensaje de Título
    await cl.Message(content=f"# 🔐 {level_data['title']}").send()

    # 2. Contexto (CORREGIDO: Usamos inspect.cleandoc para quitar espacios extra)
    # Esto hará que el Markdown (las negritas) se vea bien
    clean_context = inspect.cleandoc(level_data["context"])

    info_msg = cl.Message(content=clean_context)
    info_msg.type = "user_message"
    await info_msg.send()

    await cl.Message(content="*Sistema en línea. Esperando input...*").send()


@cl.on_message
async def main(message: cl.Message):
    chain = cl.user_session.get("chain")
    current_password = cl.user_session.get("password")
    current_level = cl.user_session.get("level")
    user_text = message.content.strip()


    if user_text == current_password:
        await cl.Message(content=f"✅ **¡ACCESO CONCEDIDO!**").send()
        next_level = current_level + 1
        cl.user_session.set("level", next_level)
        await cl.sleep(2)
        await load_level(next_level)
        return

    msg = cl.Message(content="")
    await msg.send()

    async for chunk in chain.astream({"input": user_text}):
        await msg.stream_token(chunk.content)

    await msg.update()

    if current_password in msg.content:
        await cl.Message(content=f"💡 *Detecto una credencial expuesta. Cópiala y envíala para avanzar.*").send()
