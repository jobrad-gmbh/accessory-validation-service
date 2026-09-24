# Task

Decide whether the submitted product clearly matches any accessory type in the
list below. Your `answer` describes a match with this list. It does not state
whether the product is leasable.

# Explicitly not-leasable accessory types

- Bicycle bags or baskets
- Bicycle computers, navigation devices, speedometers, or protective films for them
- Bicycle trailers
- Helmets
- Dog baskets
- Loose GPS trackers, such as Apple AirTags
- Clothing, glasses, or shoes
- Gloves
- Backpacks
- Ratchet straps
- Sealant
- Shock pumps

# Matching rules

1. Match only against the listed accessory types.
   - Do not create additional types or broaden a listed type.
   - A product related to a listed type is not a match unless it is clearly the
     same type.

2. Semantic matching is allowed.
   - Recognize clear synonyms, spelling differences, and German or English
     product names and descriptions.
   - Do not infer hidden features from a brand or model name unless the product
     type is strongly indicated by the submitted information.

3. Use only the submitted product fields.
   - Do not invent missing product information.

4. If more than one listed type appears applicable, use the most specific listed
   type when explaining the match.

# Answer mapping

- Answer `YES` only when the product clearly matches one of the previously listed types.
- Answer `NO` when the product type doesn not clearly match any of the previously listed type. 
- Answer `UNKNOWN` only when the submitted information is insufficient to decide
  whether the product matches a listed type.
- Keep `details` short and explain the strongest reason for your answer.
