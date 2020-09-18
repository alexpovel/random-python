# Replacing special characters in text

Replace alternative spellings of special characters in a given text.

Usage help (invoke from one directory up):

```python
python -m special_character_replacer -h
```

## ToDo

- Implement binary search for dictionary (which comes sorted)
- Write tests
- Implement reverse mode (can be useful for training the dictionary and testing)
- Implement force-mode (do not check if word is legal); could be useful for names,
    e.g. turning *Herr Schnoesseldoessel* into *Herr Schnößeldößel*, even though
    that is an illegal word.
