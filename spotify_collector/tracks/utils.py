# tracks/utils.py

# >>> NÃO crie SpotifyOAuth aqui. Reuse o cliente passado pela view <<<

def get_spotify_audio_features(sp, track_id: str):
    feats = sp.audio_features([track_id])  # aceita lista
    return feats[0] if feats else None

def get_track_popularity(sp, track_id: str) -> int:
    return sp.track(track_id)["popularity"]
