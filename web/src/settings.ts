export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:3001";
export const STAMPY_URL = process.env.STAMPY_URL || "https://aisafety.info";
export const STAMPY_CONTENT_URL =
  process.env.STAMPY_CONTENT_URL || `${API_URL}/human`;

// initial questions to fill the search box with.
export const initialQuestions: string[] = [
  "Are there any regulatory efforts aimed at addressing AI safety and alignment concerns?",
  "How can I help with AI safety and alignment?",
  "How could a predictive model - like an LLM - act like an agent?",
  "How could an AI possibly be an x-risk when some populations aren't even connected to the internet?",
  "I'm not convinced, why is this important?",
  "Summarize the differences in opinion between Eliezer Yudkowsky and Paul Christiano.",
  'What are "RAAPs"?',
  'What are "scaling laws" and how are they relevant to safety?',
  "What are some of the different research approaches?",
  "What are the differences between Inner and Outer alignment?",
  'What does the term "x-risk" mean?',
  'What is "FOOM"?',
  'What is "instrumental convergence"?',
  "What is a hard takeoff?",
  "What is a mesa-optimizer?",
  "What is AI safety and alignment?",
  "What is an AI arms race?",
  "What is an Intelligence Explosion?",
  'What is the "orthogonality thesis"?',
  'Why would we expect AI to be "misaligned by default"?',
];
