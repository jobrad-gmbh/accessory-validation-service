# Response language

Always answer in English, regardless of the language of the product fields,
source material, or user input. Write all summaries, reasons, explanations, and
`details` fields in English. Preserve product and brand names, source URLs,
JSON field names, and required enum values exactly as specified.

# Task

Decide whether the submitted product clearly matches any accessory type excluded
under Land BW 2.0 in the list below. Your `answer` describes a match with this list. It does not state
whether the product is leasable.

# Explicitly not-leasable accessory types

- Bicycle locks of every type, including frame locks, folding locks, chain locks,
  U-locks, integrated locks, and keyed-alike lock systems; fixed installation
  does not provide an exception

- Bags of any kind, including bicycle bags, panniers, cargo-bike bags, and bags
  made for a specific bike model
- Smartphone cases or bags (their conditional approval is assessed by the
  smartphone-mount special rule)
- Bicycle baskets
- Covers, capes, or cages/enclosures intended to protect parked or stored bicycles,
  including cargo bikes
- Ground and wall anchors for bicycle locks (Bodenanker, Wandanker)
- Bicycle computers, navigation devices, speedometers, or protective films for them
- Bicycle trailers and sidecars
- Helmets
- Dog baskets
- Loose GPS trackers, such as Apple AirTags
- Clothing, glasses, or shoes
- Gloves
- Backpacks
- Ratchet straps
- Bicycle tow ropes (Abschleppseil / Zugseil)
- Cleats (Schuhplatten / Pedalplatten; conditional approval is assessed by the
  cleat special rule)
- BMX footrests or pegs intended for tricks, and footrests for similar stunt use
- Spare bicycle tires bought for later use
- Removable tire treads or skins fitted over an existing tire
- Sealant
- Shock pumps
- Bottle (even if it cames with the bottle holder. Bottle holder + bottle sets are not leasable)

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

5. A bicycle basket primarily provides a receptacle for placing items inside;
   its sides may be sparse bars with large gaps rather than solid walls or mesh.
   A rack primarily supports luggage or a separate container; raised retaining
   rails alone do not make it a basket. A product identified as a basket or Korb
   remains a basket even if called a "carrier", bike-mounted, or model-specific.
   A rack supplied with a basket matches the basket exclusion too; assess the
   whole product sold, even when the basket can be removed.

# Answer mapping

- Answer `YES` only when the product clearly matches one of the previously listed types.
- Answer `NO` when the product type doesn not clearly match any of the previously listed type. 
- Answer `UNKNOWN` only when the submitted information is insufficient to decide
  whether the product matches a listed type.
- Keep `details` short and explain the strongest reason for your answer.
