"""Domain services for contacts formatting and vCard generation."""


class VCardFormatterService:
    """Pure domain service for generating and parsing vCard 3.0 representations."""

    @staticmethod
    def generate_vcard(
        name: str,
        firstname: str = "",
        surname: str = "",
        email: str = "",
        phone: str = "",
        organization: str = "",
        note: str = "",
    ) -> str:
        """Generates a standard vCard 3.0 text block."""
        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{name.strip()}",
            f"N:{surname.strip()};{firstname.strip()};;;",
        ]
        if email:
            lines.append(f"EMAIL;TYPE=INTERNET:{email.strip()}")
        if phone:
            lines.append(f"TEL;TYPE=CELL:{phone.strip()}")
        if organization:
            lines.append(f"ORG:{organization.strip()}")
        if note:
            # Escape newlines
            escaped_note = note.replace("\n", "\\n").replace("\r", "")
            lines.append(f"NOTE:{escaped_note}")
        lines.append("END:VCARD")
        return "\r\n".join(lines) + "\r\n"

    @staticmethod
    def parse_vcard_fields(vcard_text: str) -> dict[str, str]:
        """Extracts key attributes (FN, EMAIL, TEL, ORG, NOTE) from vCard 3.0 text."""
        result: dict[str, str] = {
            "name": "",
            "firstname": "",
            "surname": "",
            "email": "",
            "phone": "",
            "organization": "",
            "note": "",
        }
        if not vcard_text:
            return result

        for line in vcard_text.splitlines():
            line = line.strip()
            if line.startswith("FN:"):
                result["name"] = line[3:].strip()
            elif line.startswith("N:"):
                parts = line[2:].split(";")
                if len(parts) >= 1:
                    result["surname"] = parts[0].strip()
                if len(parts) >= 2:
                    result["firstname"] = parts[1].strip()
            elif line.startswith("EMAIL") and ":" in line:
                result["email"] = line.split(":", 1)[1].strip()
            elif line.startswith("TEL") and ":" in line:
                result["phone"] = line.split(":", 1)[1].strip()
            elif line.startswith(("ORG:", "ORG;")):
                result["organization"] = line.split(":", 1)[1].strip()
            elif line.startswith(("NOTE:", "NOTE;")):
                raw_note = line.split(":", 1)[1].strip()
                result["note"] = raw_note.replace("\\n", "\n")

        return result
