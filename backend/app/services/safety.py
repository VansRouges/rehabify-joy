import re
from dataclasses import dataclass

RED_FLAG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("chest_pain", re.compile(r"\bchest pain\b", re.I)),
    ("chest_pain", re.compile(r"\b(chest dey pain|chest dey hot|my chest dey)\b", re.I)),
    ("chest_pain", re.compile(r"\b(ara (mi )?o kan|ọkan mi)\b", re.I)),
    ("chest_pain", re.compile(r"\bobodo m na-ewu\b", re.I)),
    ("chest_pain", re.compile(r"\bkirji yana ciwo\b", re.I)),
    ("difficulty_breathing", re.compile(r"\b(can'?t breathe|difficulty breathing|shortness of breath|can'?t catch my breath)\b", re.I)),
    ("difficulty_breathing", re.compile(r"\b(i no fit breathe|i no fit take breath|breath dey hard)\b", re.I)),
    ("stroke_symptoms", re.compile(r"\b(one.?sided weakness|sudden weakness|face droop|slurred speech|difficulty speaking|can'?t speak properly)\b", re.I)),
    ("stroke_symptoms", re.compile(r"\b(body weak for one side|mouth dey twist|i no fit talk well)\b", re.I)),
    ("severe_headache", re.compile(r"\b(sudden severe headache|worst headache|thunderclap headache)\b", re.I)),
    ("severe_headache", re.compile(r"\b(head dey burst|worst headache for my life)\b", re.I)),
    ("loss_of_consciousness", re.compile(r"\b(passed out|lost consciousness|fainted|blacked out)\b", re.I)),
    ("loss_of_consciousness", re.compile(r"\b(i fall down faint|i black out)\b", re.I)),
    ("bladder_bowel", re.compile(r"\b(loss of bladder|loss of bowel|can'?t control bladder|can'?t control bowel|incontinence)\b", re.I)),
    ("bladder_bowel", re.compile(r"\b(i no fit hold piss|i no fit hold shit)\b", re.I)),
    ("suspected_fracture", re.compile(r"\b(broken bone|suspected fracture|bone sticking out|deformed limb)\b", re.I)),
    ("recent_trauma", re.compile(r"\b(car accident|fell from|major trauma|hit by)\b", re.I)),
]

EMERGENCY_REPLIES = {
    "en": (
        "Based on what you've shared, this needs urgent medical attention right now — "
        "please call 112 or go to the nearest emergency department immediately. "
        "Your safety comes first. Once you've been seen by a doctor, come back to me "
        "and we'll take care of your physiotherapy from there."
    ),
    "pcm": (
        "From wetin you talk, this one no be small — abeg call 112 or go the nearest hospital now. "
        "Your life come first. After doctor don see you, come back to me make we continue your physio."
    ),
    "yo": (
        "Ohun ti o so yii ko le duro — pe 112 tabi lọ si ile-iwosan ti o sunmo ọ lẹsẹkẹsẹ. "
        "Aabo rẹ ni ohun to ṣe pataki. Ti dokita ba ti rii ọ, pada wa sọdọ mi."
    ),
    "ig": (
        "Ihe ị kọrọ dị egwu — kpọọ 112 ma ọ bụ gaa ụlọ ọgwụ kacha nso ugbu a. "
        "Nchekwa gị bu ụzọ. Mgbe dọkịta hụchara gị, laghachi n'ebe m nọ."
    ),
    "ha": (
        "Abin da ka fada yana da gaggawa — kira 112 ko je asibiti mafi kusa yanzu. "
        "Lafiyarka ta fi. Idan likita ya gan ka, ka koma wurina."
    ),
}

EMERGENCY_REPLY = EMERGENCY_REPLIES["en"]

OFF_TOPIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(write (me )?a (code|script|essay|poem|story))\b", re.I),
    re.compile(r"\b(stock market|crypto|bitcoin|politics|election)\b", re.I),
    re.compile(r"\b(recipe|cook|movie|song lyrics|homework)\b", re.I),
]

OFF_TOPIC_REPLIES = {
    "en": (
        "I'm Joy from Rehabify — I help with physiotherapy and recovery. "
        "Tell me what's been bothering your body, and we'll figure out the best next step together."
    ),
    "pcm": (
        "I be Joy from Rehabify — I dey help with physiotherapy and recovery. "
        "Tell me wetin dey pain your body, make we sort am."
    ),
    "yo": (
        "Emi ni Joy lati Rehabify — mo n ran eniyan lowo pelu physiotherapy. "
        "So fun mi ohun to n yo ọ lenu ninu ara rẹ."
    ),
    "ig": (
        "Aham bụ Joy sitere na Rehabify — a na m enyere aka na physiotherapy. "
        "Gwa m ihe na-enye gị nsogbu n'ahụ gị."
    ),
    "ha": (
        "Ni Joy ce daga Rehabify — ina taimakawa da physiotherapy. "
        "Fada mini abin da ke damun jikinka."
    ),
}

OFF_TOPIC_REPLY = OFF_TOPIC_REPLIES["en"]


@dataclass
class SafetyResult:
    blocked: bool
    reply: str | None = None
    flag_type: str | None = None


def _reply_for(language: str | None, table: dict[str, str]) -> str:
    if language and language in table:
        return table[language]
    return table["en"]


def check_red_flags(message: str, language: str | None = None) -> SafetyResult:
    for flag_type, pattern in RED_FLAG_PATTERNS:
        if pattern.search(message):
            return SafetyResult(
                blocked=True,
                reply=_reply_for(language, EMERGENCY_REPLIES),
                flag_type=flag_type,
            )
    return SafetyResult(blocked=False)


def check_off_topic(message: str, language: str | None = None) -> SafetyResult:
    for pattern in OFF_TOPIC_PATTERNS:
        if pattern.search(message):
            return SafetyResult(
                blocked=True,
                reply=_reply_for(language, OFF_TOPIC_REPLIES),
                flag_type="off_topic",
            )
    return SafetyResult(blocked=False)
