import psycopg2
from psycopg2 import sql
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import requests
from bs4 import BeautifulSoup


def format_game_params(players, time, age):
    if "много" in players.lower():
        players = "10+"
    if "мин" not in time.lower():
        time = f"{time} мин."
    age = age.replace("лет", "").replace("года", "").strip()
    return players, time, age

def parse_nastolki_ur():
    all_games = []
    base_url = 'https://nastolki-ur.ru/shop/'

    for page_num in range(1, 124):
        url = f'{base_url}page/{page_num}/' if page_num > 1 else base_url
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        products = soup.find_all('li', class_='product')
        print(f"Парсинг страницы {page_num}... Найдено {len(products)} товаров.")

        for product in products:
            title_tag = product.find('div', class_='woocommerce-loop-product__title')
            price_tag = product.find('span', class_='woocommerce-Price-amount')
            link_tag = product.find('a', class_='woocommerce-LoopProduct-link')
            params = product.find('div', class_='params')

            rating_tag = product.find('strong', class_='rating')
            rating = 0
            if rating_tag:
                try:
                    rating = float(rating_tag.text.strip())
                except ValueError:
                    rating = 0

            if title_tag and price_tag and link_tag:
                title = title_tag.text.strip()
                price_text = price_tag.text.strip().replace('₽', '').replace(' ', '').replace(',', '.')
                try:
                    price = float(price_text)
                except ValueError:
                    continue

                link = link_tag['href']

                players = "Не указано"
                time = "Не указано"
                age = "Не указано"

                if params:
                    players_tag = params.find('div', class_='kolichestvo-igrokov')
                    time_tag = params.find('div', class_='vremya-partii')
                    age_tag = params.find('div', class_='min-age')

                    if players_tag:
                        players = players_tag.text.strip()
                    if time_tag:
                        time = time_tag.text.strip()
                    if age_tag:
                        age = age_tag.text.strip()

                    players, time, age = format_game_params(players, time, age)

                all_games.append({
                    'title': title, 'price': price, 'link': link, 'rating': rating,
                    'players': players, 'time': time, 'age': age, 'is_popular': False, 'comments_count': 0
                })

        print(f"Записано {len(products)} товаров с страницы {page_num}.")

    return all_games

def parse_znaemigraem():
    all_games = []
    base_url = 'https://chel.znaemigraem.ru/catalog'

    for page_num in range(1, 177):
        url = f'{base_url}?PAGEN_1={page_num}' if page_num > 1 else base_url
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        games = soup.find_all('div', class_='item')
        print(f"Парсинг страницы {page_num}... Найдено {len(games)} товаров.")

        for game in games:
            title_tag = game.find('a', class_='name')
            price_tag = game.find('span', class_='catalog-item__price')
            price_out_tag = game.find('span', class_='catalog-item__price_out')
            rating_tag = game.find('div', class_='rating')
            props = game.find('div', class_='props')

            comments_tag = game.find('a', class_='comments')
            comments_count = 0
            if comments_tag:
                try:
                    comments_count = int(comments_tag.text.strip().split()[0])
                except ValueError:
                    comments_count = 0

            if not (price_tag or price_out_tag):
                price = None
            else:
                price_text = (price_tag or price_out_tag).text.strip().replace('₽', '').replace('р.', '').replace(' ', '').replace(',', '.')
                try:
                    price = float(price_text) if price_text else None
                except ValueError:
                    price = None

            if title_tag:
                title = title_tag.text.strip()
                link = f"https://chel.znaemigraem.ru{title_tag['href']}"

                rating = 0
                if rating_tag:
                    rating = rating_tag.get('title', '0')
                    try:
                        rating = int(rating)
                    except ValueError:
                        rating = 0

                players = "Не указано"
                time = "Не указано"
                age = "Не указано"

                if props:
                    players_tag = props.find('div', title='Количество игроков')
                    time_tag = props.find('div', title='Время игры')
                    age_tag = props.find('div', title='Возраст игроков')

                    if players_tag:
                        players = players_tag.text.strip()
                    if time_tag:
                        time = time_tag.text.strip()
                    if age_tag:
                        age = age_tag.text.strip()

                    players, time, age = format_game_params(players, time, age)

                is_popular = bool(game.find('span', class_='label hit'))

                all_games.append({
                    'title': title, 'price': price, 'link': link, 'rating': rating,
                    'players': players, 'time': time, 'age': age, 'is_popular': is_popular, 'comments_count': comments_count
                })

        print(f"Записано {len(games)} товаров с страницы {page_num}.")

    return all_games

def insert_games_to_db(games):
    try:
        conn = psycopg2.connect(
            dbname='tg_bot_db',
            user='postgres',
            password='postgres',
            host='db',
            port='5432'
        )
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO search_info (title, price, link, rating, players, time, age, is_popular, comments_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for game in games:
            cursor.execute(insert_query, (
                game['title'], game['price'], game['link'], game['rating'],
                game['players'], game['time'], game['age'], game['is_popular'], game['comments_count']
            ))

        conn.commit()
        print(f'{len(games)} игр добавлено в базу данных.')

    except Exception as e:
        print(f"Ошибка при добавлении данных в базу: {e}")
    finally:
        cursor.close()
        conn.close()


def get_all_games_from_db():
    try:
        conn = psycopg2.connect(
            dbname='tg_bot_db',
            user='postgres',
            password='postgres',
            host='db',
            port='5432'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM search_info")
        rows = cursor.fetchall()

        all_games = [
            {
                'id': row[0],
                'title': row[1],
                'price': row[2],
                'link': row[3],
                'rating': row[4],
                'players': row[5],
                'time': row[6],
                'age': row[7],
                'is_popular': row[8],
                'comments_count': row[9]
            }
            for row in rows
        ]

        return all_games

    except Exception as e:
        print(f"Ошибка при получении данных из базы: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def _search_game_by_name(all_games, name, threshold=80):
    game_titles = [game['title'] for game in all_games]
    results = process.extract(name, game_titles, limit=None, scorer=fuzz.partial_ratio)

    filtered_results = []
    for result in results:
        if result[1] >= threshold:
            game_index = game_titles.index(result[0])
            filtered_results.append(all_games[game_index])

    return filtered_results

def search_game_by_name(game_title):
    try:
        connection = psycopg2.connect(
            dbname='tg_bot_db',
            user='postgres',
            password='postgres',
            host='db',
            port='5432'
        )
        cursor = connection.cursor()
        query = "SELECT * FROM search_info WHERE title ILIKE %s;"
        cursor.execute(query, (f'%{game_title}%',))

        column_names = [desc[0] for desc in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(column_names, row)))
    
    except Exception as e:
        if hasattr(e, 'message'):
            print(e.message)
        else:
            print(e)
        return None
    finally:
        cursor.close()
        connection.close()
    
    return results


def main():
    print("Парсинг сайтов...")
    nastolki_ur_data = parse_nastolki_ur()
    znaemigraem_data = parse_znaemigraem()

    insert_games_to_db(nastolki_ur_data + znaemigraem_data)

    all_games = get_all_games_from_db()

    while True:
        game_name = input("Введите название игры (или 'выход' для завершения): ").strip()

        if game_name.lower() == 'выход':
            print("Выход из программы.")
            break

        results = search_game_by_name(all_games, game_name)

        if results:
            print("\n=== Результаты поиска ===")
            for game in results:
                print(f"Название: {game['title']}")
                print(f"Цена: {game['price']} руб.")
                print(f"Ссылка: {game['link']}")
                print(f"Игроки: {game['players']}")
                print(f"Время игры: {game['time']}")
                print(f"Возраст: {game['age']}")
                print(f"Рейтинг: {game['rating']} звёзд")

            cheapest_game = min(results, key=lambda x: x['price'] if x['price'] is not None else float('inf'))
            print(f"\nСамая дешёвая игра: {cheapest_game['title']} - {cheapest_game['price']} руб.")
            print(f"Ссылка: {cheapest_game['link']}")

            highest_rated_game = max(results, key=lambda x: x['rating'] if x['rating'] is not None else 0)
            print(f"Самая рейтинговая игра: {highest_rated_game['title']} - Рейтинг: {highest_rated_game['rating']}")
            print(f"Ссылка: {highest_rated_game['link']}")

            most_popular_game = max(results, key=lambda x: (x['rating'] if x['rating'] is not None else 0) + x['comments_count'])
            print(f"Самая популярная игра: {most_popular_game['title']}")
            print(f"Ссылка: {most_popular_game['link']}")

        else:
            print("Игра не найдена на обоих сайтах.")


if __name__ == "__main__":
    main() 
