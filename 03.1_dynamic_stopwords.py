import os
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load API keys from your .env file
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "gdelt_Data")
DB_PATH = os.path.join(DATA_DIR, "gdelt_brain.db")

# Standard 318 English Stop Words (Our unbreakable baseline)
BASE_STOP_WORDS = {"a", "about", "above", "across", "after", "afterwards", "again", "against", "all", "almost", "alone", "along", "already", "also", "although", "always", "am", "among", "amongst", "amoungst", "amount", "an", "and", "another", "any", "anyhow", "anyone", "anything", "anyway", "anywhere", "are", "around", "as", "at", "back", "be", "became", "because", "become", "becomes", "becoming", "been", "before", "beforehand", "behind", "being", "below", "beside", "besides", "between", "beyond", "bill", "both", "bottom", "but", "by", "call", "can", "cannot", "cant", "co", "con", "could", "couldnt", "cry", "de", "describe", "detail", "do", "done", "down", "due", "during", "each", "eg", "eight", "either", "eleven", "else", "elsewhere", "empty", "enough", "etc", "even", "ever", "every", "everyone", "everything", "everywhere", "except", "few", "fifteen", "fifty", "fill", "find", "fire", "first", "five", "for", "former", "formerly", "forty", "found", "four", "from", "front", "full", "further", "furthermore", "get", "give", "go", "had", "has", "hasnt", "have", "he", "hence", "her", "here", "hereafter", "hereby", "herein", "hereupon", "hers", "herself", "him", "himself", "his", "how", "however", "hundred", "i", "ie", "if", "in", "inc", "indeed", "interest", "into", "is", "it", "its", "itself", "keep", "last", "latter", "latterly", "least", "less", "ltd", "made", "many", "may", "me", "meanwhile", "might", "mill", "mine", "more", "moreover", "most", "mostly", "move", "much", "must", "my", "myself", "name", "namely", "neither", "never", "nevertheless", "next", "nine", "no", "nobody", "none", "noone", "nor", "not", "nothing", "now", "nowhere", "of", "off", "often", "on", "once", "one", "only", "onto", "or", "other", "others", "otherwise", "our", "ours", "ourselves", "out", "over", "own", "part", "per", "perhaps", "please", "put", "rather", "re", "same", "see", "seem", "seemed", "seeming", "seems", "serious", "several", "she", "should", "show", "side", "since", "sincere", "six", "sixty", "so", "some", "somehow", "someone", "something", "sometime", "sometimes", "somewhere", "still", "such", "system", "take", "ten", "than", "that", "the", "their", "them", "themselves", "then", "thence", "there", "thereafter", "thereby", "therefore", "therein", "thereupon", "these", "they", "thick", "thin", "third", "this", "those", "though", "three", "through", "throughout", "thru", "thus", "to", "together", "too", "top", "toward", "towards", "twelve", "twenty", "two", "un", "under", "until", "up", "upon", "us", "very", "via", "was", "we", "well", "were", "what", "whatever", "when", "whence", "whenever", "where", "whereafter", "whereas", "whereby", "wherein", "whereupon", "wherever", "whether", "which", "while", "whither", "who", "whoever", "whole", "whom", "whose", "why", "will", "with", "within", "without", "would", "yet", "you", "your", "yours", "yourself", "yourselves"}

def get_deepseek_stopwords(word_list):
    """Sends the top words to DeepSeek and asks it to identify the junk."""
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    words_str = ", ".join(word_list)
    
    prompt = f"""
    You are an expert data engineer cleaning a dataset of global news headlines. 
    Below is a list of the most frequently used words in our news database over the last 30 days.
    
    Identify all words that act as "stop words" or meaningless journalistic filler. 
    This includes:
    1. Grammatical filler (e.g., says, said, told, will)
    2. News/Media filler (e.g., news, live, update, report, daily, times, video, photo)
    3. Generic time/location markers (e.g., today, week, year, city, state)
    4. Junk hex codes or broken encoding (e.g., xf3, x430)
    
    DO NOT include important nouns, verbs, or adjectives that denote actual news events (e.g., strike, protest, election, murder, storm, president).
    
    RETURN ONLY A COMMA-SEPARATED LIST OF THE STOP WORDS. Do not use markdown, bullet points, or introductory text.
    
    Words to analyze:
    {words_str}
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful data cleaning assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        raw_output = response.choices[0].message.content
        new_stopwords = [w.strip().lower() for w in raw_output.split(',')]
        return set(new_stopwords)
    except Exception as e:
        print(f"❌ DeepSeek API Error: {e}")
        return set()

def run_janitor():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Step 03A: Dynamic Stop Word Janitor...")
    
    if datetime.today().weekday() != 6:
        print(">>> Not Sunday. Skipping dynamic stop word generation. Saving API costs!")
        return

    print(">>> It's Sunday! Waking up the LLM to clean the vocabulary...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        query = '''
            SELECT word 
            FROM cluster_word_memory
            GROUP BY word
            ORDER BY SUM(docs_with_word) DESC
            LIMIT 2500
        '''
        df = pd.read_sql_query(query, conn)
        top_words = df['word'].tolist()
    except Exception as e:
        print(f"⚠️ Could not read memory bank: {e}")
        conn.close()
        return

    print(f"Sending {len(top_words)} words to DeepSeek for analysis...")
    dynamic_stopwords = get_deepseek_stopwords(top_words)
    print(f"DeepSeek identified {len(dynamic_stopwords)} filler words.")

    final_stop_words = BASE_STOP_WORDS.union(dynamic_stopwords)

    cursor.execute('DROP TABLE IF EXISTS custom_stopwords')
    cursor.execute('CREATE TABLE custom_stopwords (word TEXT PRIMARY KEY)')
    
    insert_data = [(w,) for w in final_stop_words if w.strip()]
    cursor.executemany('INSERT OR IGNORE INTO custom_stopwords VALUES (?)', insert_data)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Success! {len(insert_data)} total stop words locked into the database for the week.")

if __name__ == '__main__':
    run_janitor()
