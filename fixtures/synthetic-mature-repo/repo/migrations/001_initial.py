from src.db import Base


def upgrade():
    conn = Base.metadata.bind.connect()
    conn.execute("CREATE TABLE wardrobes (id serial primary key, owner_id int, name text)")
    conn.execute("CREATE TABLE outfits (id serial primary key, wardrobe_id int, label text)")
    conn.commit()