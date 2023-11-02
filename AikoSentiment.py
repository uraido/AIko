'''
AikoSentiment.py

pip install:
- azure-ai-textanalytics

'''


from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient

key_file = open('keys/key_azuresentiment.txt', 'r').read().split('\n')
key = key_file[0]
endpoint = key_file[1]


def sentiment_analysis(text: str):
    text_analytics_client = TextAnalyticsClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    texts = [text]

    result = text_analytics_client.analyze_sentiment(texts)
    sentiment = result[0].sentiment
    #match sentiment:
    if sentiment == 'positive':
        #case 'positive':
        score = int(result[0].confidence_scores.positive * 100)
    elif sentiment == 'neutral':
        score = int(result[0].confidence_scores.neutral * 100)
    elif sentiment == 'negative':
        score = int(result[0].confidence_scores.negative * 100)

    return sentiment, score


if __name__ == '__main__':
    print(sentiment_analysis("I think you are cute."))
    print(sentiment_analysis("I don't think you are cute."))
    print(sentiment_analysis("I think."))
