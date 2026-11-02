"""Atendimento pela linha de comando.

    python src/main.py                         conversa interativa
    python src/main.py entrada.txt saida.md    roda as mensagens do arquivo (uma por linha) e salva a conversa
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from agent import MusicaAgent

ROOT = Path(__file__).resolve().parent.parent
EXIT_WORDS = {"sair", "exit", "quit"}


def build_agent() -> MusicaAgent:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        sys.exit("LLM_API_KEY não definida. Copie .env.example para .env e preencha a chave do OpenRouter.")
    return MusicaAgent(api_key=api_key)


def interactive():
    agent = build_agent()
    print("Empório da Música - atendimento com a Marina")
    print("Digite 'sair' para encerrar.\n")
    while True:
        try:
            message = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if message.lower() in EXIT_WORDS:
            break
        if not message:
            continue
        try:
            print(f"\nMarina: {agent.process_message(message)}\n")
        except Exception as exc:
            print(f"\n[erro ao falar com o modelo: {exc}]\n")


def from_file(input_file: str, output_file: str = None):
    agent = build_agent()
    messages = [line.strip() for line in Path(input_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    transcript = []
    for message in messages:
        reply = agent.process_message(message)
        print(f"Você: {message}\nMarina: {reply}\n")
        transcript.append(f"**Cliente:** {message}\n\n**Marina:** {reply}\n")
    if output_file:
        header = (
            f"<!-- Gerado por `python src/main.py {input_file} {output_file}` em "
            f"{datetime.now():%d/%m/%Y %H:%M}, modelo {agent.model}. Texto não editado. -->\n\n"
        )
        Path(output_file).write_text(header + "\n---\n\n".join(transcript), encoding="utf-8")
        print(f"Conversa salva em {output_file}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        from_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        interactive()
