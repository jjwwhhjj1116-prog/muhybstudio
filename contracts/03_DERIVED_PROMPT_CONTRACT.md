# Flow·영상 파생 계약

## Flow

`flow[i] = visualization.scene[i].english_image_prompt`

라벨·장면 번호·CTA·END를 제거하고 내용은 임의 축약하지 않는다.

## 영상

`video[i]`는 같은 `scene_number`의 이미지를 움직이는 간단한 지시이며 새 스토리 정보를 추가하지 않는다.

## 해시

Flow와 영상 항목은 `source_scene_hash`를 저장한다. 시각화 장면 해시가 바뀌면 파생물은 `INVALIDATED`다.

## 수량 불변식

`visualization_count == flow_count == video_count == N`

`flow_blank_lines == video_blank_lines == N - 1`
