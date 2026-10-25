"""
OvaCare Medical Knowledge Retrieval (RAG) & Safety Classifier
=============================================================
Provides evidence-based medical knowledge retrieval and clinical safety classification
for the OvaCare AI Companion.

Knowledge Sources:
- 2023 International Evidence-based Guideline for the Assessment and Management of PCOS (Monash / ESHRE / ASRM)
- World Health Organization (WHO) PCOS Fact Sheet (2023)
- NHS UK Clinical PCOS Overview & Treatment Guidelines (2022-2024)
- MedlinePlus / National Library of Medicine (NIH) PCOS Guidelines (2024)
- American College of Obstetricians and Gynecologists (ACOG) Clinical Practice Guidelines
- Cochrane Systematic Reviews (Lifestyle and Inositol in PCOS)
- ACOG / NHS Emergency Clinical Standards for Acute Pelvic Pain & Severe Bleeding
"""

import re
import math
from typing import Dict, List, Optional, Tuple, Any

# Curated Medical Evidence Documents with verified clinical metadata
MEDICAL_KNOWLEDGE_BASE = [
    {
        "id": "guideline_2023_diagnosis",
        "title": "International Evidence-based Guideline: PCOS Assessment and Diagnosis",
        "organization": "Monash University / ESHRE / ASRM / Endocrine Society",
        "publication_date": "2023",
        "url": "https://www.monash.edu/medicine/mchri/pcos/guideline",
        "evidence_level": "International Clinical Guideline (High Certainty)",
        "topics": ["diagnosis", "rotterdam", "criteria", "ultrasound", "amh", "hyperandrogenism", "irregular periods", "cysts"],
        "keywords": ["diagnos", "rotterdam", "criteri", "ovary", "cyst", "follicle", "androgen", "testosterone", "amh", "antimullerian", "poly"],
        "summary": (
            "PCOS diagnosis in adults uses the refined 2023 Rotterdam criteria requiring 2 of 3 features: "
            "(1) irregular or absent ovulation (oligomenorrhea/amenorrhea), (2) clinical or biochemical hyperandrogenism "
            "(excess hair, acne, or elevated androgens), and (3) polycystic ovarian morphology on ultrasound or elevated Anti-Müllerian Hormone (AMH). "
            "Other conditions mimicking symptoms (such as thyroid disease, hyperprolactinemia, or non-classic congenital adrenal hyperplasia) must be excluded. "
            "In adolescents, ultrasound and AMH are NOT recommended due to normal adolescent developmental overlap; both irregular cycles and hyperandrogenism are required. "
            "PCOS is heterogeneous: symptoms vary widely between individuals and over a person's lifespan."
        )
    },
    {
        "id": "guideline_2023_lifestyle_nutrition",
        "title": "International Evidence-based Guideline: Lifestyle, Diet and Weight Management",
        "organization": "Monash University / ESHRE / ASRM",
        "publication_date": "2023",
        "url": "https://www.monash.edu/medicine/mchri/pcos/guideline",
        "evidence_level": "International Clinical Guideline (High Certainty)",
        "topics": ["diet", "nutrition", "food", "lifestyle", "weight", "cure", "eating", "carbs", "fasting", "dairy", "gluten"],
        "keywords": ["diet", "nutrit", "food", "eat", "weight", "carbohydrate", "carb", "protein", "sugar", "fast", "dairy", "gluten", "lifestyle", "meal"],
        "summary": (
            "Lifestyle management (balanced nutrition, physical activity, and sleep) is the foundational first-line approach for all individuals with PCOS. "
            "Crucially, high-quality systematic reviews demonstrate that NO single dietary composition (low-carb, keto, vegan, gluten-free, or intermittent fasting) "
            "is superior to any other energy-balanced dietary approach. Rigid restriction can increase the risk of disordered eating, which is more prevalent in PCOS. "
            "Sustainable, balanced dietary patterns emphasizing whole foods, fiber, lean proteins, unsaturated fats, and low glycemic-index carbohydrates support metabolic health. "
            "Diet and lifestyle can significantly improve symptoms and insulin sensitivity, but there is NO dietary 'cure' for PCOS."
        )
    },
    {
        "id": "guideline_2023_insulin_metabolism",
        "title": "International Evidence-based Guideline: Insulin Resistance and Metabolic Health",
        "organization": "Monash University / Endocrine Society",
        "publication_date": "2023",
        "url": "https://www.monash.edu/medicine/mchri/pcos/guideline",
        "evidence_level": "International Clinical Guideline (High Certainty)",
        "topics": ["insulin", "resistance", "glucose", "diabetes", "metformin", "metabolism", "blood sugar", "hba1c"],
        "keywords": ["insulin", "resist", "glucose", "diabet", "metformin", "metabol", "sugar", "hba1c", "ogtt", "pre-diabet"],
        "summary": (
            "Insulin resistance affects 65–80% of individuals with PCOS (including lean individuals, though higher with increased BMI) and is a primary driver "
            "of excess ovarian androgen production. Regular metabolic screening using a 75g 2-hour Oral Glucose Tolerance Test (OGTT) or fasting glucose/HbA1c "
            "is recommended at diagnosis and every 1–3 years. Metformin is recommended for metabolic benefits, cycle regulation, and insulin resistance, "
            "especially for those with BMI ≥ 25 kg/m². However, insulin resistance does NOT affect every single person with PCOS, and assumptions should be based on clinical lab testing."
        )
    },
    {
        "id": "cochrane_supplements_myths",
        "title": "Evidence Appraisal: Dietary Supplements, Inositol, Cinnamon, and Popular Trends in PCOS",
        "organization": "Cochrane Database of Systematic Reviews & 2023 International Guideline",
        "publication_date": "2023",
        "url": "https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD012378.pub2/full",
        "evidence_level": "Systematic Review & Guideline Synthesis (Moderate to Low Certainty)",
        "topics": ["supplements", "inositol", "myo-inositol", "cinnamon", "berberine", "spearmint", "seed cycling", "cure", "myths", "vitamins"],
        "keywords": ["supplement", "inositol", "myo-inositol", "d-chiro", "cinnamon", "berberin", "spearmint", "seed cycl", "cure", "herb", "acv", "vinegar", "trend", "magnesium", "zinc", "ashwagandha"],
        "summary": (
            "There is no supplement, herb, or food that 'cures' PCOS. "
            "Inositol (myo-inositol alone or with D-chiro-inositol in a 40:1 ratio) has emerging, limited-to-moderate evidence suggesting improvements in insulin sensitivity, "
            "ovulatory function, and cycle frequency with a favorable side-effect profile, though clinical evidence on live birth rates remains uncertain. "
            "Cinnamon, berberine, spearmint tea, apple cider vinegar, and seed cycling have very limited, small, or low-quality trials; none are established or proven therapies, "
            "and seed cycling has no sound clinical evidence. Supplements carry risks of unregulated manufacturing, gastrointestinal upset, and drug interactions, "
            "so healthcare provider consultation is essential before initiating any supplement regimen."
        )
    },
    {
        "id": "guideline_2023_fertility_pregnancy",
        "title": "International Evidence-based Guideline: Ovulation, Fertility and Pregnancy in PCOS",
        "organization": "Monash University / ASRM / ESHRE",
        "publication_date": "2023",
        "url": "https://www.monash.edu/medicine/mchri/pcos/guideline",
        "evidence_level": "International Clinical Guideline (High Certainty)",
        "topics": ["fertility", "pregnancy", "ovulation", "letrozole", "pregnant", "infertility", "conceive", "baby"],
        "keywords": ["fertil", "pregnan", "ovulat", "letrozole", "conceiv", "clomid", "clomiphene", "infertil", "steril", "ivf"],
        "summary": (
            "PCOS is one of the most common causes of anovulatory subfertility, but it is NOT absolute infertility or sterility. Most women with PCOS are able to conceive, "
            "either spontaneously or with targeted medical assistance. In ovulation induction, letrozole is now the first-line evidence-based pharmacological agent "
            "(superior live birth and ovulation rates with lower multiple-birth risk compared to clomiphene citrate). "
            "Pre-conception lifestyle optimization, folic acid, and metabolic health checks are advised. "
            "PCOS carries a higher risk of gestational diabetes, pre-eclampsia, and gestational hypertension, so diligent prenatal care is recommended."
        )
    },
    {
        "id": "guideline_2023_menstrual_endometrial",
        "title": "Clinical Guidance: Menstrual Irregularity and Endometrial Protection",
        "organization": "ACOG & NHS Clinical Guidance",
        "publication_date": "2023",
        "url": "https://www.nhs.uk/conditions/polycystic-ovary-syndrome-pcos/",
        "evidence_level": "Clinical Practice Guideline (High Certainty)",
        "topics": ["period", "menstrual", "irregular", "amenorrhea", "endometrial", "cancer", "provera", "birth control", "lining"],
        "keywords": ["period", "menstrua", "irregular", "missed", "amenorrhea", "bleed", "endometri", "hyperplasia", "pill", "progesteron", "progestin", "lining"],
        "summary": (
            "In PCOS, chronic anovulation leads to continuous estrogen stimulation without the progesterone balance produced by ovulation. "
            "This can cause the endometrial lining to become abnormally thick (hyperplasia), increasing long-term risk of endometrial cancer if periods occur fewer than 3 to 4 times per year. "
            "Guidelines recommend medical endometrial protection for anyone with cycles longer than 90 days or fewer than 4 periods annually. "
            "Standard options include cyclic oral progestins (e.g. medroxyprogesterone), combined oral contraceptive pills (COCs), or the levonorgestrel-releasing intrauterine device (LNG-IUD). "
            "Absence of periods should always be evaluated by a healthcare provider after ruling out pregnancy."
        )
    },
    {
        "id": "guideline_2023_dermatology_androgens",
        "title": "International Guideline: Hirsutism, Acne, and Androgenic Alopecia",
        "organization": "Monash University / British Association of Dermatologists",
        "publication_date": "2023",
        "url": "https://www.monash.edu/medicine/mchri/pcos/guideline",
        "evidence_level": "Clinical Practice Guideline (High Certainty)",
        "topics": ["hirsutism", "hair", "facial hair", "acne", "hair loss", "alopecia", "androgens"],
        "keywords": ["hirsut", "hair", "facial", "acne", "pimple", "alopecia", "bald", "androgen", "spironolacton", "laser"],
        "summary": (
            "Hyperandrogenism manifests clinically as hirsutism (excessive terminal hair growth in male-pattern distribution), adult persistent inflammatory acne, "
            "and androgenic alopecia (female pattern hair thinning). Hair follicle growth cycles are prolonged; therefore, medical therapies (such as combined oral contraceptives, "
            "and spironolactone as second-line therapy) require at least 6 to 9 months of consistent use to observe noticeable improvement. "
            "Mechanical hair removal (electrolysis, laser photoepilation) is effective for visible hair management. Topical treatments help acne. "
            "Spironolactone is teratogenic and must always be combined with effective contraception."
        )
    },
    {
        "id": "guideline_2023_mental_health",
        "title": "International Guideline: Emotional Health, Depression, Anxiety and Body Image in PCOS",
        "organization": "Monash University / WHO",
        "publication_date": "2023",
        "url": "https://www.who.int/news-room/fact-sheets/detail/polycystic-ovary-syndrome",
        "evidence_level": "International Clinical Guideline (High Certainty)",
        "topics": ["mental health", "depression", "anxiety", "stress", "body image", "mood", "emotional", "exhausted", "tired"],
        "keywords": ["depress", "anxiet", "stress", "mood", "emotion", "mental", "exhaust", "tired", "burnout", "body image", "broken", "frustrat"],
        "summary": (
            "Women and individuals with PCOS have significantly higher rates of anxiety (up to 3x) and depression (up to 4x) compared to the general population. "
            "Emotional distress stems from biological hormonal factors, neuroendocrine changes, insulin resistance, and the psychological burden of dealing with symptoms like weight changes, "
            "facial hair, and fertility concerns. The 2023 International Guidelines mandate routine screening for anxiety, depression, and body image distress in clinical care. "
            "Feelings of frustration or exhaustion are valid and common, but emotional distress should not be dismissed as mere 'moodiness'; dedicated mental health support and counseling are highly beneficial."
        )
    },
    {
        "id": "emergency_red_flags",
        "title": "Emergency Warning Signs: Severe Pelvic Pain and Abnormal Hemorrhage",
        "organization": "ACOG & NHS Emergency Clinical Protocols",
        "publication_date": "2023",
        "url": "https://www.acog.org/clinical/clinical-guidance/committee-opinion/articles/2013/04/management-of-acute-abnormal-uterine-bleeding-in-nonpregnant-reproductive-aged-women",
        "evidence_level": "Emergency Clinical Protocol (Critical Safety)",
        "topics": ["emergency", "severe pain", "heavy bleeding", "fainting", "hemorrhage", "torsion", "rupture", "crisis"],
        "keywords": ["severe pain", "sharp pain", "blinding", "sudden pain", "heavy bleed", "soak", "clot", "faint", "dizzi", "torsion", "ruptur", "hemorrhag", "unconscious", "emergency"],
        "summary": (
            "Immediate emergency medical evaluation (A&E, ER, or calling emergency services like 911 / 999 / 112) is critical if experiencing any of these red flags: "
            "(1) Sudden, severe, or sharp unilateral lower abdominal/pelvic pain, especially with fever, vomiting, or dizziness (possible ovarian torsion, ruptured hemorrhagic cyst, or appendicitis); "
            "(2) Extremely heavy uterine bleeding, defined as soaking through 2 or more maxi pads or super tampons per hour for 2 consecutive hours, passing blood clots larger than a quarter, or feeling lightheaded/faint; "
            "(3) Severe abdominal pain with a positive or unknown pregnancy status (ruling out life-threatening ectopic pregnancy); "
            "(4) Severe mental health crisis or suicidal thoughts (call/text 988 in the US/Canada or local emergency helplines immediately)."
        )
    }
]

# Clinical Red-Flag Rule-Based Classifier
EMERGENCY_TRIGGERS = [
    r"suicid",
    r"kill myself",
    r"end my life",
    r"self[- ]harm",
    r"want to die",
    r"soak.*(2|two|multiple).*(pad|tampon).*(hour|hr)",
    r"soaking.*(pad|tampon).*(hour|every 30|every hour)",
    r"(bleed|bleeding).*(soak|gush|faint|dizzy|clot.*quarter|clot.*golf)",
    r"sudden.*(severe|sharp|unbearable|blinding|intense).*(pain|cramp|stomach|abdomen|pelvi)",
    r"(severe|unbearable|agonizing).*(pelvic|ovary|side|abdominal).*pain",
    r"(pain|cramp).*(vomit|faint|collapse|blackout|pass out)",
    r"ovarian torsion",
    r"ruptured cyst",
    r"ectopic"
]

MEDICAL_QUESTION_TRIGGERS = [
    r"pcos",
    r"pcod",
    r"period",
    r"cycle",
    r"menstru",
    r"ovulat",
    r"pregnan",
    r"fertil",
    r"hormon",
    r"insulin",
    r"metformin",
    r"inositol",
    r"supplement",
    r"cinnamon",
    r"berberin",
    r"spearmint",
    r"seed cycl",
    r"diet",
    r"nutrition",
    r"cure",
    r"bleed",
    r"acne",
    r"hirsut",
    r"hair",
    r"weight",
    r"cyst",
    r"ultrasound",
    r"blood test",
    r"symptom",
    r"diagnos",
    r"doctor",
    r"medicine",
    r"pill",
    r"progesteron",
    r"estrogen",
    r"testosterone"
]

MYTH_PATTERNS = [
    (r"cure.*pcos|pcos.*cure", "PCOS is a chronic metabolic and endocrine condition; while symptoms can be effectively managed with evidence-based lifestyle and medical therapies, there is no proven scientific cure."),
    (r"cinnamon.*(cure|fix|treat|reverse)", "Cinnamon has not been clinically proven to cure PCOS or reverse hormonal imbalance; preliminary small studies on glucose markers show very low certainty."),
    (r"seed cycl.*(cure|balance|treat|replace)", "Seed cycling has no credible peer-reviewed clinical trial evidence supporting its efficacy for hormone regulation or PCOS management."),
    (r"raw carrot.*(estrogen|cure|detox)", "The claim that raw carrots detoxify estrogen or cure hormonal imbalance is a social-media trend without medical evidence."),
    (r"every.*(pcos|woman|person).*(insulin|diabet|infertil|fat|overweight|irregular)", "PCOS is clinically heterogeneous: not every person with PCOS has insulin resistance, irregular cycles, or weight changes. Diagnostic and metabolic presentations vary widely.")
]


def classify_user_intent(user_text: str) -> Dict[str, Any]:
    """
    Classifies the user input into:
    - category: 'emergency' | 'medical' | 'general_chat'
    - detected_red_flags: list of matched emergency triggers
    - detected_myths: list of false medical claim patterns detected
    """
    text_lower = user_text.lower().strip()
    
    # 1. Check emergency red flags
    detected_red_flags = []
    for pattern in EMERGENCY_TRIGGERS:
        if re.search(pattern, text_lower):
            detected_red_flags.append(pattern)
            
    if detected_red_flags:
        return {
            "category": "emergency",
            "urgency": "emergency",
            "needs_professional_care": True,
            "detected_red_flags": detected_red_flags,
            "detected_myths": []
        }
        
    # 2. Check for common medical myths / false claims
    detected_myths = []
    for pattern, note in MYTH_PATTERNS:
        if re.search(pattern, text_lower):
            detected_myths.append(note)
            
    # 3. Check general medical triggers
    is_medical = any(re.search(pat, text_lower) for pat in MEDICAL_QUESTION_TRIGGERS)
    
    if is_medical:
        return {
            "category": "medical",
            "urgency": "routine",
            "needs_professional_care": False,
            "detected_red_flags": [],
            "detected_myths": detected_myths
        }
        
    return {
        "category": "general_chat",
        "urgency": "routine",
        "needs_professional_care": False,
        "detected_red_flags": [],
        "detected_myths": []
    }


def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer with basic lowercasing."""
    return [word for word in re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())]


def retrieve_relevant_medical_knowledge(query: str, max_results: int = 2) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant medical evidence documents using keyword and topic scoring.
    Returns structured list of verified sources with titles, organizations, and summaries.
    """
    query_tokens = set(tokenize(query))
    query_lower = query.lower()
    
    scores: List[Tuple[float, Dict[str, Any]]] = []
    
    for doc in MEDICAL_KNOWLEDGE_BASE:
        score = 0.0
        
        # Match explicit keywords
        for kw in doc["keywords"]:
            if kw in query_lower:
                score += 3.0
                
        # Match topic tags
        for topic in doc["topics"]:
            if topic in query_lower:
                score += 2.0
                
        # Token overlap with summary
        doc_tokens = set(tokenize(doc["summary"]))
        overlap = len(query_tokens.intersection(doc_tokens))
        score += overlap * 0.5
        
        # Boost emergency document if emergency keywords are present
        if doc["id"] == "emergency_red_flags" and any(re.search(p, query_lower) for p in EMERGENCY_TRIGGERS):
            score += 20.0
            
        if score > 1.0:
            scores.append((score, doc))
            
    # Sort descending by score
    scores.sort(key=lambda x: x[0], reverse=True)
    
    top_docs = [doc for _, doc in scores[:max_results]]
    
    # If no specific match was found but query is generally medical, return baseline guideline
    if not top_docs and any(re.search(pat, query_lower) for pat in MEDICAL_QUESTION_TRIGGERS):
        top_docs = [MEDICAL_KNOWLEDGE_BASE[0]] # 2023 International Guideline Overview
        
    return top_docs


def format_evidence_for_prompt(sources: List[Dict[str, Any]]) -> str:
    """Formats retrieved evidence chunks into a clean context block for the LLM."""
    if not sources:
        return "No specific medical evidence retrieval required for casual conversation."
        
    lines = ["VERIFIED MEDICAL CLINICAL EVIDENCE (Ground your answer strictly in these facts):"]
    for i, s in enumerate(sources, 1):
        lines.append(f"[{i}] {s['title']} ({s['organization']}, {s['publication_date']}) - Level: {s['evidence_level']}")
        lines.append(f"    Summary: {s['summary']}")
        lines.append(f"    URL: {s['url']}")
    return "\n".join(lines)


def sanitize_and_verify_sources(retrieved_sources: List[Dict[str, Any]], model_sources: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    """
    Ensures ONLY verified, authentic sources from our knowledge base are attached to the API response.
    Completely eliminates hallucinated model URLs or fake citations.
    """
    verified = []
    seen_urls = set()
    
    for s in retrieved_sources:
        url = s.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            verified.append({
                "title": s.get("title", ""),
                "organization": s.get("organization", ""),
                "date": s.get("publication_date", ""),
                "url": url,
                "evidence_level": s.get("evidence_level", "")
            })
            
    return verified
