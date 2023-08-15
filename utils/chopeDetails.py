def parseTags(tags_unparsed):
    cleaned_s = tags_unparsed.strip().replace("\n", "").replace("\t", "")  # Remove newline and tab characters
    cuisine_list = [cuisine.strip() for cuisine in cleaned_s.split(',')]  # Split by comma and strip individual items
    return cuisine_list