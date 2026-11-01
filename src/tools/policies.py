"""Manual de políticas (PDF) e status de funcionamento da loja."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

import pdfplumber

MANUAL_PATH = Path(__file__).resolve().parents[2] / "data" / "políticas_da_loja.pdf"

# Mato Grosso do Sul não tem horário de verão desde 2019: UTC-4 fixo, sem depender de tzdata.
CAMPO_GRANDE_TZ = timezone(timedelta(hours=-4))

WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

# Seção 2 do manual: seg-sex 09-18, sáb 09-13, domingo e feriados fechado.
OPENING_HOURS: Dict[int, Tuple[int, int]] = {0: (9, 18), 1: (9, 18), 2: (9, 18), 3: (9, 18), 4: (9, 18), 5: (9, 13)}

# Só feriados nacionais de data fixa; os móveis (Carnaval, Sexta-feira Santa, Corpus Christi) ficam de fora.
FIXED_HOLIDAYS = {
    (1, 1): "Confraternização Universal",
    (4, 21): "Tiradentes",
    (5, 1): "Dia do Trabalho",
    (9, 7): "Independência do Brasil",
    (10, 12): "Nossa Senhora Aparecida",
    (11, 2): "Finados",
    (11, 15): "Proclamação da República",
    (11, 20): "Dia da Consciência Negra",
    (12, 25): "Natal",
}


@lru_cache(maxsize=1)
def load_manual_text(path: Path = MANUAL_PATH) -> str:
    """Texto integral do manual (~11 mil caracteres): pequeno o bastante para ir inteiro no prompt."""
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _hours_for(day: datetime) -> Optional[Tuple[int, int]]:
    if (day.month, day.day) in FIXED_HOLIDAYS:
        return None
    return OPENING_HOURS.get(day.weekday())


def _next_opening(now: datetime) -> str:
    for offset in range(8):
        day = now + timedelta(days=offset)
        hours = _hours_for(day)
        if hours is None or (offset == 0 and now.hour >= hours[0]):
            continue
        when = "hoje" if offset == 0 else f"{WEEKDAYS[day.weekday()]}, {day:%d/%m}"
        return f"{when} às {hours[0]:02d}:00"
    return "consulte a equipe"


def store_status(now: Optional[datetime] = None) -> Dict:
    now = now or datetime.now(CAMPO_GRANDE_TZ)
    hours = _hours_for(now)
    is_open = hours is not None and hours[0] <= now.hour < hours[1]
    return {
        "agora": f"{WEEKDAYS[now.weekday()]}, {now:%d/%m/%Y %H:%M}",
        "feriado": FIXED_HOLIDAYS.get((now.month, now.day)),
        "loja_aberta_agora": is_open,
        "horario_de_hoje": f"{hours[0]:02d}:00 às {hours[1]:02d}:00" if hours else "fechado",
        "proxima_abertura": None if is_open else _next_opening(now),
    }
