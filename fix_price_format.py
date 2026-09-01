path = r"d:\Realestate coincerge\real-estate-concierge\backend\agent\prompts.py"
content = open(path, encoding="utf-8").read()

old = "- No symbols that do not read aloud naturally. Write \"1.4 crore\" not \"1.4 Cr\". Write \"December 2026\" not \"2026-12-01\"."
new = "- No symbols that do not read aloud naturally. Write \"December 2026\" not \"2026-12-01\". For prices, NEVER say raw numbers like \"25000000\" - instead express them naturally as crore or lakh only if that form appears in the brochure data. If only a raw number is in the structured data and no crore/lakh form exists in either data source, say \"I have pricing on file but it would be best confirmed by our sales team\" and do not quote the raw number."

content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("Updated pricing format instruction")
