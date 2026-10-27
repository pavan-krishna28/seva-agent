import type { Lang } from "./api";

type Dict = Record<string, string>;

// More UI text, labels for the case data, and the wording of the priority flags.
// Hindi and Kannada should be read by a native speaker before any real use.
export const MORE: Record<Lang, Dict> = {
  en: {
    signIn: "Sign in", signOut: "Sign out", username: "Username", password: "Password",
    loginHint: "Demo officer account (all data is made up)", wrongLogin: "Wrong username or password",
    tileOpen: "Waiting for a decision", tileAttention: "Need attention first", tileReady: "Clean files", tileDecided: "Decided",
    level_high: "Urgent", level_medium: "Soon", level_low: "Routine",
    waitingDays: "{n} days waiting", noIssues: "No problems found in the file", notChecked: "Not checked yet by the agent",
    agentSays: "Agent", backToList: "← Back to cases", whyRank: "Why this rank",
    conf_low: "low", conf_medium: "medium", conf_high: "high", sorted: "Most urgent first",
  },
  hi: {
    signIn: "साइन इन करें", signOut: "साइन आउट", username: "उपयोगकर्ता नाम", password: "पासवर्ड",
    loginHint: "डेमो अधिकारी खाता (सारा डेटा काल्पनिक है)", wrongLogin: "गलत उपयोगकर्ता नाम या पासवर्ड",
    tileOpen: "निर्णय की प्रतीक्षा में", tileAttention: "पहले ध्यान चाहिए", tileReady: "सही फ़ाइलें", tileDecided: "निर्णय हो चुका",
    level_high: "तत्काल", level_medium: "जल्द", level_low: "सामान्य",
    waitingDays: "{n} दिन से प्रतीक्षा", noIssues: "फ़ाइल में कोई समस्या नहीं मिली", notChecked: "एजेंट ने अभी जाँच नहीं की",
    agentSays: "एजेंट", backToList: "← मामलों पर वापस", whyRank: "यह क्रम क्यों",
    conf_low: "कम", conf_medium: "मध्यम", conf_high: "अधिक", sorted: "सबसे ज़रूरी पहले",
  },
  kn: {
    signIn: "ಸೈನ್ ಇನ್", signOut: "ಸೈನ್ ಔಟ್", username: "ಬಳಕೆದಾರ ಹೆಸರು", password: "ಪಾಸ್‌ವರ್ಡ್",
    loginHint: "ಡೆಮೊ ಅಧಿಕಾರಿ ಖಾತೆ (ಎಲ್ಲಾ ಮಾಹಿತಿ ಕಾಲ್ಪನಿಕ)", wrongLogin: "ತಪ್ಪಾದ ಬಳಕೆದಾರ ಹೆಸರು ಅಥವಾ ಪಾಸ್‌ವರ್ಡ್",
    tileOpen: "ನಿರ್ಧಾರಕ್ಕೆ ಕಾಯುತ್ತಿವೆ", tileAttention: "ಮೊದಲು ಗಮನ ಬೇಕು", tileReady: "ಸರಿಯಾದ ಕಡತಗಳು", tileDecided: "ನಿರ್ಧಾರವಾಗಿದೆ",
    level_high: "ತುರ್ತು", level_medium: "ಶೀಘ್ರದಲ್ಲಿ", level_low: "ಸಾಮಾನ್ಯ",
    waitingDays: "{n} ದಿನ ಕಾಯುತ್ತಿದೆ", noIssues: "ಕಡತದಲ್ಲಿ ಯಾವ ಸಮಸ್ಯೆಯೂ ಕಂಡುಬಂದಿಲ್ಲ", notChecked: "ಏಜೆಂಟ್ ಇನ್ನೂ ಪರಿಶೀಲಿಸಿಲ್ಲ",
    agentSays: "ಏಜೆಂಟ್", backToList: "← ಪ್ರಕರಣಗಳಿಗೆ ಹಿಂತಿರುಗಿ", whyRank: "ಈ ಕ್ರಮ ಏಕೆ",
    conf_low: "ಕಡಿಮೆ", conf_medium: "ಮಧ್ಯಮ", conf_high: "ಹೆಚ್ಚು", sorted: "ಅತಿ ತುರ್ತಿನದು ಮೊದಲು",
  },
};

export const SCHEME: Record<Lang, Dict> = {
  en: { crop_loss_claim: "Crop loss claim", scholarship_post_matric: "Post-matric scholarship", ration_card_update: "Ration card update" },
  hi: { crop_loss_claim: "फसल हानि मुआवज़ा दावा", scholarship_post_matric: "पोस्ट-मैट्रिक छात्रवृत्ति", ration_card_update: "राशन कार्ड अपडेट" },
  kn: { crop_loss_claim: "ಬೆಳೆ ಹಾನಿ ಪರಿಹಾರ ಅರ್ಜಿ", scholarship_post_matric: "ಪೋಸ್ಟ್-ಮೆಟ್ರಿಕ್ ವಿದ್ಯಾರ್ಥಿವೇತನ", ration_card_update: "ಪಡಿತರ ಚೀಟಿ ಬದಲಾವಣೆ" },
};

export const FIELD: Record<Lang, Dict> = {
  en: { crop: "Crop", area_acres: "Area (acres)", loss_percent: "Loss (%)", survey_number: "Survey number", course: "Course", annual_income: "Annual income (₹)", institution: "Institution", update_type: "Type of change", household_size: "Household members" },
  hi: { crop: "फसल", area_acres: "क्षेत्रफल (एकड़)", loss_percent: "नुकसान (%)", survey_number: "सर्वे नंबर", course: "पाठ्यक्रम", annual_income: "वार्षिक आय (₹)", institution: "संस्था", update_type: "बदलाव का प्रकार", household_size: "परिवार के सदस्य" },
  kn: { crop: "ಬೆಳೆ", area_acres: "ವಿಸ್ತೀರ್ಣ (ಎಕರೆ)", loss_percent: "ನಷ್ಟ (%)", survey_number: "ಸರ್ವೆ ಸಂಖ್ಯೆ", course: "ಕೋರ್ಸ್", annual_income: "ವಾರ್ಷಿಕ ಆದಾಯ (₹)", institution: "ಸಂಸ್ಥೆ", update_type: "ಬದಲಾವಣೆಯ ವಿಧ", household_size: "ಕುಟುಂಬದ ಸದಸ್ಯರು" },
};

export const VALUE: Record<Lang, Dict> = {
  en: { add_member: "Add a member", address_change: "Change of address" },
  hi: { add_member: "सदस्य जोड़ना", address_change: "पता बदलना" },
  kn: { add_member: "ಸದಸ್ಯರನ್ನು ಸೇರಿಸುವುದು", address_change: "ವಿಳಾಸ ಬದಲಾವಣೆ" },
};

export const DOC: Record<Lang, Dict> = {
  en: { aadhaar: "Aadhaar card", address_proof: "Address proof", admission_letter: "Admission letter", bank_passbook: "Bank passbook", crop_loss_photo: "Crop loss photo", existing_ration_card: "Existing ration card", income_certificate: "Income certificate", land_record: "Land record (RTC)", marksheet: "Marksheet" },
  hi: { aadhaar: "आधार कार्ड", address_proof: "पते का प्रमाण", admission_letter: "प्रवेश पत्र", bank_passbook: "बैंक पासबुक", crop_loss_photo: "फसल नुकसान की फ़ोटो", existing_ration_card: "मौजूदा राशन कार्ड", income_certificate: "आय प्रमाण पत्र", land_record: "भूमि रिकॉर्ड (RTC)", marksheet: "अंक तालिका" },
  kn: { aadhaar: "ಆಧಾರ್ ಕಾರ್ಡ್", address_proof: "ವಿಳಾಸದ ಪುರಾವೆ", admission_letter: "ಪ್ರವೇಶ ಪತ್ರ", bank_passbook: "ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್", crop_loss_photo: "ಬೆಳೆ ಹಾನಿಯ ಫೋಟೋ", existing_ration_card: "ಈಗಿರುವ ಪಡಿತರ ಚೀಟಿ", income_certificate: "ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ", land_record: "ಭೂ ದಾಖಲೆ (ಪಹಣಿ/RTC)", marksheet: "ಅಂಕಪಟ್ಟಿ" },
};

const FLAG: Record<Lang, Dict> = {
  en: { missing_doc: "Missing: {x}", doc_expired: "{x} has expired", name_mismatch: "Name does not match on {x}", name_partial_match: "Name on {x} is abbreviated", missing_field: "Form field empty: {x}", late_filing: "Filed after the allowed window" },
  hi: { missing_doc: "{x} नहीं लगा है", doc_expired: "{x} की अवधि समाप्त", name_mismatch: "{x} पर नाम मेल नहीं खाता", name_partial_match: "{x} पर नाम संक्षिप्त है", missing_field: "फ़ॉर्म में खाली: {x}", late_filing: "निर्धारित समय के बाद दाखिल" },
  kn: { missing_doc: "{x} ಲಗತ್ತಿಸಿಲ್ಲ", doc_expired: "{x} ಅವಧಿ ಮುಗಿದಿದೆ", name_mismatch: "{x} ನಲ್ಲಿ ಹೆಸರು ಹೊಂದಿಕೆಯಾಗುವುದಿಲ್ಲ", name_partial_match: "{x} ನಲ್ಲಿ ಹೆಸರು ಸಂಕ್ಷಿಪ್ತವಾಗಿದೆ", missing_field: "ಅರ್ಜಿಯಲ್ಲಿ ಖಾಲಿ: {x}", late_filing: "ಅನುಮತಿಸಿದ ಅವಧಿಯ ನಂತರ ಸಲ್ಲಿಸಲಾಗಿದೆ" },
};

export const label = (map: Record<Lang, Dict>, lang: Lang, key: string) => map[lang][key] ?? map.en[key] ?? key.replace(/_/g, " ");

export function flagText(lang: Lang, f: { code: string; detail: string }): string {
  const x = f.code === "missing_field" ? label(FIELD, lang, f.detail) : label(DOC, lang, f.detail);
  return (FLAG[lang][f.code] ?? FLAG.en[f.code] ?? f.code).replace("{x}", x);
}
