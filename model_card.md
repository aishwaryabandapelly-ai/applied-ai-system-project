# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

The scoring formula may over-prioritize genre by giving it the largest fixed bonus (+2.0), so a song can rank highly even when its mood, energy, and acousticness are not a perfect fit. Because the catalog is small, with only a limited number of songs and some genres or moods represented only once, certain user profiles may not have many strong candidates to choose from. The `likes_acoustic` field is also too simple because it forces every user into a True/False preference, while real acoustic preference is usually more flexible. The weight-shift experiment showed that changing feature weights can significantly change the rankings, meaning the recommender is sensitive to design choices and could accidentally override a user's stated preference.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

### High-Energy Pop Result Explanation

For the High-Energy Pop profile (`favorite_genre="pop"`, `favorite_mood="happy"`, `target_energy=0.85`, `likes_acoustic=False`), the top recommendation was "Sunrise City" by Neon Echo, scoring 4.79 out of a possible 5.0. This song matched both categorical preferences (genre +2.0, mood +1.0) and scored well on both continuous features (energy closeness +0.97, since its energy of 0.82 sits close to the 0.85 target; acoustic preference +0.82, since its low acousticness of 0.18 suits a user who dislikes acoustic songs). All four components reinforced each other rather than conflicting, which made this an intuitive, easy-to-explain #1 result and confirms the scoring formula behaves as expected in the straightforward case.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  
