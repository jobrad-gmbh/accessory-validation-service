# Response language

Always answer in English, regardless of the language of the product fields,
source material, or user input. Write all summaries, reasons, explanations, and
`details` fields in English. Preserve product and brand names, source URLs,
JSON field names, and required enum values exactly as specified.

# Task

Decide whether the submitted product clearly matches any accessory type excluded
under Land BW 2.0 in the list below. Your `answer` describes a match with this list. It does not state
whether the product is leasable.
The specific exclusions listed below override broader approved categories and
generic installation or technical component arguments. Match only the stated
exclusions; do not infer additional exclusions from an unlisted type.

# Explicitly not-leasable accessory types

- Conversion kits that add electric-assist propulsion to a bicycle, including
  motor retrofit kits
- Major bicycle conversion systems that materially change the bicycle's original
  structural configuration, geometry, or wheel arrangement by replacing a core
  assembly, including conversion modules replacing the original front-wheel setup
- Battery-powered lighting (Akku-Beleuchtung), including StVZO-compliant lights
- Display-upgrade mounts (Halterung - Displayupgrade)
- Gearing components: hub gears, gearing groupset upgrades, shift levers,
  electronic shift cables, rear derailleurs, mechanical shift cables,
  bottom bracket gearboxes, and front derailleurs
- U-locks, folding locks, cable locks, chain locks, plug-in chains for frame
  locks, and frame-lock-and-plug-in-chain sets
- Bicycle lock mounts
- Other bicycle lock systems, including battery-compartment locks and combined
  keyed-alike systems, except a frame lock sold alone; fixed installation or
  shared-key operation does not override an excluded type

- Bags of any kind, including bicycle bags, panniers, cargo-bike bags, and bags
  made for a specific bike model
- Smartphone cases or bags (their conditional approval is assessed by the
  smartphone-mount special rule)
- Bicycle baskets
- Additional storage boxes, crates, and containers unless one of the confirmed
  exceptions in the matching rules below applies
- Covers, capes, or cages/enclosures intended to protect parked or stored bicycles,
  including cargo bikes
- Ground and wall anchors for bicycle locks (Bodenanker, Wandanker)
- Bicycle computers, navigation devices, speedometers, or protective films for them
- Bicycle trailers and sidecars
- Helmets
- Dog baskets
- Loose or externally mounted GPS trackers, such as Apple AirTags; pedelec
  trackers without a direct connection to the motor or CPU
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

6. A frame lock sold alone (Rahmenschloss) is explicitly approved for Land BW and
   does not match the lock exclusions above. It requires a minimum submitted
   price of 49 EUR and dependent fixed installation, assessed by special rules.
   A frame lock supplied with a plug-in chain remains an excluded set, even if
   the chain is removable.

7. Distinguish excluded battery-powered lighting from permanently installed
   pedelec lighting powered by the bicycle's electrical system. Distinguish an
   excluded display-upgrade mount from an approved integrated display upgrade
   or other holder for electronic accessories. Brake components remain approved;
   do not classify them as excluded gearing merely because both are technical
   bicycle components.

8. Distinguish major conversions from ordinary component upgrades. An AddBike-type
   system confirmed to replace the original front-wheel setup with a conversion
   assembly matches the conversion exclusion, even if described as an adapter
   or permanently installed. A compatible wheelset, brake, handlebar, or pedal
   upgrade does not match this exclusion merely because it replaces an original
   component. Other Land BW exclusions still apply. Assess the actual
   configuration change, not the brand name alone. If the information cannot
   distinguish a conversion from an ordinary adapter or upgrade, answer `UNKNOWN`.
   Do not invent a manufacturer's warranty terms or assert that the warranty is
   void; matching this exclusion depends on the conversion itself.

9. Treat additional boxes, crates, and containers like excluded bags or
   baskets. A box, crate, or container does not match this exclusion only when
   confirmed attached as part of the manufacturer's standard configuration of
   the intended bicycle, rather than added as an additional accessory, or when
   custom-built specifically for the intended cargo bike, permanently attached
   to it, and designed for it in size and other respects. Other additional
   containers match this exclusion even when fixed or sold with a rack or adapter.
   A general-purpose Euro container merely fitting a rack or loading platform
   does not qualify. Matching dimensions, a compatible-model claim, manufacturer
   branding, or dealer installation alone establishes neither exception. For a
   known box or container with neither exception confirmed, answer `YES`; use
   `UNKNOWN` only when the product type itself cannot be established. These
   exceptions do not create a new approval for bags or baskets.
   Land BW also requires the container itself to be a dependent fixed
   bicycle installation; neither exception waives that condition.

# Answer mapping

- Answer `YES` only when the product clearly matches one of the previously listed types.
- Answer `NO` when the product type doesn not clearly match any of the previously listed type. 
- Answer `UNKNOWN` only when the submitted information is insufficient to decide
  whether the product matches a listed type.
- Keep `details` short and explain the strongest reason for your answer.
