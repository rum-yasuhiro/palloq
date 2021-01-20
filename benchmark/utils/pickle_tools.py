import pickle

def pickle_dump(obj, path):
    with open(path, mode='wb') as f:
        pickle.dump(obj, f)


def pickle_load(path):
    with open(path, mode='rb') as f:
        data = pickle.load(f)
        return data
