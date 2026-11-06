"""
Ortak Yardımcı Fonksiyonlar — Türkçe Karakter ve Arama Normalizasyonu
"""

TR_MAP = str.maketrans({
    'İ': 'i', 'I': 'i', 'ı': 'i',
    'ğ': 'g', 'Ğ': 'g',
    'ü': 'u', 'Ü': 'u',
    'ş': 's', 'Ş': 's',
    'ö': 'o', 'Ö': 'o',
    'ç': 'c', 'Ç': 'c'
})


def tr_normalize(text: str) -> str:
    """Metni Türkçe ve ASCII toleranslı küçük harfe dönüştürür."""
    if not text:
        return ""
    return str(text).translate(TR_MAP).lower()


def tr_contains(query: str, target: str) -> bool:
    """Hedef metin içinde sorgunun var olup olmadığını Türkçe karakter uyumlu arar."""
    if not query:
        return True
    if not target:
        return False
    return tr_normalize(query).strip() in tr_normalize(target)
