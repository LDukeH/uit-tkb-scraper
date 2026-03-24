from typing import Any

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

def label_announcements(data_list: list[dict[Any, Any]]):
    documents = [training_set[0] for training_set in training_sets]
    labels = [training_set[1] for training_set in training_sets]
    test_documents = [data["title"] for data in data_list]
    bow_vectorizer = CountVectorizer()
    vectors = bow_vectorizer.fit_transform(documents)
    test_vectors = bow_vectorizer.transform(test_documents)
    label_dictionary = __create_label_dictionary(labels)
    index_dictionary = __swap_dictionary_key_value(label_dictionary)
    index_labels = [label_dictionary[label] for label in labels]
    classifier = MultinomialNB()
    classifier.fit(vectors, index_labels)
    predictions = classifier.predict(test_vectors)
    # Apply the labels
    for i in range(len(data_list)):
        data_list[i]["topic"] = index_dictionary[predictions[i]]
    return data_list

def __create_label_dictionary(labels: list[str]) -> dict[str, int]:
    label_dictionary = dict.fromkeys(labels, 0)
    index = 0
    for key in label_dictionary:
        label_dictionary[key] = index
        index += 1
    return label_dictionary

def __swap_dictionary_key_value(dictionary: dict[str, int]) -> dict[int, str]:
    return {value: key for key, value in dictionary.items()}

training_sets = [
    (
        "Kết quả ĐKHP (đợt 2) và TKB học kỳ 2 năm học 2025-2026_Chương trình chuẩn.",
        "ĐKHP"
    ),
    (
        "Kết quả ĐKHP (đợt 1) học kỳ 2 năm học 2025-2026_Chương trình chuẩn.",
        "ĐKHP"
    ),
    (
        "Dạy-học online từ ngày 23/02/2026 đến ngày 01/3/2026",
        "Schedule"
    ),
    (
        "Thông tin chương trình Student Exchange Program at Chiba University (J-PAC)",
        "Misc"
    ),
    (
        "Thông báo về việc đăng ký học phần của sinh viên",
        "ĐKHP"
    ),
    (
        "Thông báo lịch thi cuối học kỳ 1 năm học 2025-2026 các lớp VB2_đợt 2",
        "Schedule"
    ),
    (
        "Thông báo thu học phí học kỳ 2 năm học 2025-2026 trình độ đại học",
        "HP"
    ),
    (
        "Thông báo dạy bù online trong dịp nghỉ bù lễ Tết Dương lịch 2026",
        "Schedule"
    ),
    (
        "Thông báo lịch ĐKHP và TKB (dự kiến) HK2 năm học 2025-2026",
        "ĐKHP"
    ),
    (
        "Cập nhật kết quả xét miễn anh văn - Thông báo về việc xét miễn các môn anh văn 1, 2 và 3 trong học kỳ 2 năm học 2025-2026 cho sinh viên chính quy chương trình đào tạo đại trà và chương trình chuẩn",
        "Misc"
    ),
    (
        "Thông báo khảo sát ý kiến SV về hoạt động giảng dạy của GV HKI - NH 2025-2026",
        "Misc"
    ),
    (
        "Danh sách chính thức lớp Huredee 7 học tiếng Nhật miễn phí và tư vấn việc làm tại Nhật Bản do tổ chức Huredee tài trợ",
        "Misc"
    ),
    (
        "Nộp hồ sơ du học Viện Công nghệ IIST, Đại học Hosei",
        "Misc"
    ),
    (
        "Thông báo Lịch học ôn tập Olympic Toán năm học 2025-2026",
        "Schedule"
    ),
    (
        "Thông báo nhận đơn nhập học lại, bảo lưu, chuyển ngành, song ngành, thôi học HK 2 2025-2026",
        "Misc"
    ),
    (
        "Thông báo về việc nhận bằng tốt nghiệp đợt 4 năm 2025",
        "Schedule"
    ),
    (
        "Thông báo thu học phí học kỳ 1, năm học 2025-2026 trình độ ĐTĐH CT liên kết BCU, VB2CQ, LTĐH, Song ngành",
        "HP"
    ),
    (
        "Thông báo lịch thi cuối kỳ các môn Anh văn học kỳ 1 năm học 2025-2026\n        Thân chào các bạn sinh viên,",
        "Schedule"
    )
]