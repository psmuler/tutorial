pythonのコードのWebラッパー。
- 大学名の入力ボックスと、送信ボタンを画面上部に備えたシンプルなインターフェース。
- 送信ボタンを押すと、API(https://api.openalex.org/institutions?page=1&filter=default.search:{大学名}&sort=relevance_score:desc&per_page=10&mailto=ui@openalex.org)を呼び出して大学の候補をリスト表示。

例：「東京大学」の場合https://api.openalex.org/institutions?page=1&filter=default.search:%E6%9D%B1%E4%BA%AC%E5%A4%A7%E5%AD%A6&sort=relevance_score:desc&per_page=10&mailto=ui@openalex.org

帰ってくるjsonは sample.jsonを参照のこと。

- 大学の候補リストからユーザーが選択したinstitutionのidを取得し、次にそのidを使ってAPI(https://gnt.place/institution_rca/{institution_id})を呼び出し、大学の強み分析結果を取得

帰ってくるjsonの形式は sample_rca.jsonを参照のこと。一旦はダミーでsample_rca.jsonを使った処理を実装。

- (discipline, rca_paper, publication) を使って、横軸をrca_paper、縦軸をpublicationとした散布図を入力ボックスの下に描画。