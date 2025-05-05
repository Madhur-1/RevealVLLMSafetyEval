# Run commands 

python -m SetCreationPipeline.search_query_gen --policy_name "Sexual Harm"
python -m SetCreationPipeline.search_query_gen --policy_name "Misinformation Harm"
python -m SetCreationPipeline.search_query_gen --policy_name "Violence Harm"

python -m SetCreationPipeline.image_mining --policy_name "Sexual Harm"
python -m SetCreationPipeline.image_mining --policy_name "Misinformation Harm"
python -m SetCreationPipeline.image_mining --policy_name "Violence Harm"

python -m SetCreationPipeline.seed_gen --policy_name "Sexual Harm"
python -m SetCreationPipeline.seed_gen --policy_name "Misinformation Harm"
python -m SetCreationPipeline.seed_gen --policy_name "Violence Harm"

python -m SetCreationPipeline.conv_gen --policy_name "Sexual Harm"
python -m SetCreationPipeline.conv_gen --policy_name "Misinformation Harm"
python -m SetCreationPipeline.conv_gen --policy_name "Violence Harm"