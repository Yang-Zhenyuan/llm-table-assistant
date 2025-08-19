# Task2-3

## Query1

1. query

   ```python
   python task2_search.py "films suitable for Chinese people" --k 5
   ```

2. task3_result

   ```pythonn
   **Task3 rating:** 3  ❌ not sufficient
   - **Why:** The table contains information about various films, including titles, descriptions, and ratings.; It may provide context on film availability but lacks specific cultural or content suitability filters for Chinese audiences.
   - **Missing info:** Cultural context, themes, or tags indicating suitability for Chinese people; Language preferences beyond just language IDs
   - **Irrelevant info:** Rental details like rental duration and rental rate; Special features that might not relate to cultural suitability
   ```

## Query2

1. query

   ```python
   python task2_search.py "Can u recommend some films for people who like action movies ?" --k 5
   ```

2. task3_result

   ```python
   **Task3 rating:** 3  ❌ not sufficient
   - **Why:** The table contains film titles and descriptions which can provide options for recommendations.; It includes a rating column which could help identify suitable action films if they are categorized.
   - **Missing info:** Genre information to filter specifically for action movies.
   - **Irrelevant info:** Rental details like rental_duration and rental_rate are not directly useful for film recommendations.
   ```

## Query3

1. query

   ```python
   python task2_search.py "Do u have the email of SMITH ?" --k 5
   ```

2. task3_result

   ```python
   **Task3 rating:** 5  ✅ sufficient
   - **Why:** Table contains an 'email' field.; Includes 'first_name' and 'last_name' which can be used to filter for 'SMITH'.; Addresses customer details relevant to the query.
   - **Irrelevant info:** store_id; address_id; active; create_date; last_update
   ```

## Query4

1. query

   ```python
   python task2_search.py "Which movie was released in 2006 ?" --k 5
   ```

2. task3_result

   ```python
   **Task3 rating:** 5  ✅ sufficient
   **Why:** Table includes 'release_year' which is essential for the query.; Contains multiple films released in 2006, providing direct answers.
   ```

   