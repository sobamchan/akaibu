from dataclasses import dataclass

import openai
from openai import OpenAI
from pydantic import BaseModel

from akaibu.paper import Paper


class IsRelevant(BaseModel):
    does_match: bool


@dataclass(frozen=True)
class Checker:
    requirement: str
    model_name: str
    base_url: str
    key: str

    def is_paper_relevant(self, paper: Paper) -> bool:
        client = OpenAI(base_url=self.base_url, api_key=self.key)
        try:
            completion = client.beta.chat.completions.parse(
                temperature=0,
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": f"""
                        Check if the following paper matches the requirements:

                        Requirements: {self.requirement}

                        Paper:
                          Title: {paper.title}
                          Abstract: {paper.abstract}
                    """,
                    }
                ],
                response_format=IsRelevant,
            )

            response = completion.choices[0].message
            if response.parsed:
                return response.parsed.does_match
            elif response.refusal:
                print(response.refusal)
            return False
        except Exception as e:
            if type(e) is openai.LengthFinishReasonError:
                print("Too many tokens: ", e)
            else:
                print(e)
            return False
